from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from app.errors import AppError
from app.models import CashBalance, Holding, PortfolioSnapshot
from app.settings import Settings

CONFIG_DEFAULTS: dict[str, dict[str, str | bool]] = {
    "default_display_currency": {"value": "EUR", "topic": "general", "is_secret": False},
    "investor_profile": {"value": "Long-term investor focused on diversified growth.", "topic": "investor_profile", "is_secret": False},
    "investment_objectives": {"value": "Capital appreciation and diversification.", "topic": "investor_profile", "is_secret": False},
    "risk_tolerance": {"value": "moderate", "topic": "investor_profile", "is_secret": False},
    "investment_horizon": {"value": "10+ years", "topic": "investor_profile", "is_secret": False},
    "binance_api_key": {"value": "", "topic": "api_keys", "is_secret": True},
    "binance_api_secret": {"value": "", "topic": "api_keys", "is_secret": True},
    "binance_base_url": {"value": "https://api.binance.com", "topic": "api_keys", "is_secret": False},
    "genai_provider": {"value": "disabled", "topic": "genai", "is_secret": False},
    "genai_model": {"value": "", "topic": "genai", "is_secret": False},
    "google_api_key": {"value": "", "topic": "api_keys", "is_secret": True},
    "openai_api_key": {"value": "", "topic": "api_keys", "is_secret": True},
    "anthropic_api_key": {"value": "", "topic": "api_keys", "is_secret": True},
    "exchangerate_host_url": {"value": "https://api.exchangerate.host", "topic": "general", "is_secret": False},
    "asset_insight_prompt": {"value": "Analyze this asset for the investor. Asset: {asset}. Portfolio context: {portfolio}. Investor profile: {investor_profile}. Return concise facts, interpretation, risks, fit, and action options.", "topic": "prompts", "is_secret": False},
    "asset_macro_prompt": {"value": "Analyze the current macro, industry, and market context relevant to this asset. Asset: {asset}. Investor profile: {investor_profile}. Return concise implications for holding, adding, trimming, or monitoring.", "topic": "prompts", "is_secret": False},
    "portfolio_insight_prompt": {"value": "Analyze the portfolio as a system using this portfolio context: {portfolio}. Investor profile: {investor_profile}. Return executive insights, risks, diversification gaps, and practical recommendations.", "topic": "prompts", "is_secret": False},
    "asset_compare_prompt": {"value": "Compare the original asset with similar alternatives. Original asset: {asset}. Investor profile: {investor_profile}. Return a complete responsive HTML table only. Columns are assets, first column is the original asset. Rows should include ticker, asset type, market/industry, thesis, quality, valuation context, growth, risk, portfolio fit, pros, cons, confidence, and conclusion.", "topic": "prompts", "is_secret": False},
    "chat_extra_context": {"value": "Answer as an educational portfolio assistant. Be concise, practical, and aware of portfolio and investor fit.", "topic": "prompts", "is_secret": False},
}

VERSION_ENTRIES = [
    ("MVP v0.5", "database introduced"),
    ("MVP v0.3.4", "Automated GenAI insights and persistent portfolio chat"),
    ("MVP v0.3.3", "Env vars adjustments"),
    ("MVP v0.3.2", "UX improvements"),
    ("MVP v0.3.1", "Code corrections"),
    ("MVP v0.3", "added version log"),
    ("MVP v0.2", "extending the draft"),
    ("MVP v0.1", "MVP initial draft"),
]


class Database:
    def __init__(self, settings: Settings):
        self.url = settings.supabase_db_url or settings.database_url

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def _connect(self):
        if not self.url:
            raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL is required for database features.")
        try:
            return psycopg2.connect(self.url)
        except Exception as exc:
            raise AppError("Database", "opening PostgreSQL connection", f"{type(exc).__name__}: {exc}", exc) from exc

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def ensure_seed_data(self) -> None:
        if not self.configured:
            return
        try:
            with self._connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                for key, meta in CONFIG_DEFAULTS.items():
                    cur.execute(
                        """
                        insert into app_config (key, value, topic, is_secret)
                        values (%s, %s, %s, %s)
                        on conflict (key) do nothing
                        """,
                        (key, meta["value"], meta["topic"], meta["is_secret"]),
                    )
                for version, title in VERSION_ENTRIES:
                    cur.execute(
                        """
                        insert into version_log (version, title)
                        select %s, %s
                        where not exists (select 1 from version_log where version = %s and title = %s)
                        """,
                        (version, title, version, title),
                    )
                conn.commit()
                cur.close()
        except AppError:
            raise
        except Exception as exc:
            raise AppError("Database", "seeding default configuration/version log", f"{type(exc).__name__}: {exc}", exc) from exc

    def config(self) -> dict[str, str]:
        values = {key: str(meta["value"]) for key, meta in CONFIG_DEFAULTS.items()}
        if not self.configured:
            return values
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("select key, value from app_config")
            rows = cur.fetchall()
            cur.close()
        values.update({row["key"]: row["value"] for row in rows})
        return values

    def config_rows(self) -> list[dict[str, Any]]:
        if not self.configured:
            return [{"key": key, **meta, "updated_at": None} for key, meta in CONFIG_DEFAULTS.items()]
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("select key, value, topic, is_secret, updated_at from app_config order by topic, key")
            rows = cur.fetchall()
            cur.close()
            return rows

    def update_config(self, updates: dict[str, str]) -> None:
        if not self.configured:
            return
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            for key, value in updates.items():
                meta = CONFIG_DEFAULTS.get(key, {"topic": "general", "is_secret": False})
                cur.execute(
                    """
                    insert into app_config (key, value, topic, is_secret, updated_at)
                    values (%s, %s, %s, %s, now())
                    on conflict (key) do update set value = excluded.value, updated_at = now()
                    """,
                    (key, value, meta["topic"], meta["is_secret"]),
                )
            conn.commit()
            cur.close()

    def save_snapshot(self, provider: str, source: str, snapshot: PortfolioSnapshot) -> None:
        if not self.configured:
            return
        captured_at = datetime.now(timezone.utc)
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "insert into portfolio_snapshots (provider, source, captured_at) values (%s, %s, %s) returning id",
                (provider, source, captured_at),
            )
            snapshot_id = cur.fetchone()["id"]
            for item in snapshot.holdings:
                cur.execute(
                    """
                    insert into portfolio_holdings (snapshot_id, provider, section, symbol, name, quantity, currency, market_value, cost_basis, captured_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (snapshot_id, item.provider, item.section.value, item.symbol, item.name, item.quantity, item.currency, item.market_value, item.cost_basis, captured_at),
                )
            for item in snapshot.cash:
                cur.execute(
                    """
                    insert into portfolio_cash (snapshot_id, provider, currency, amount, captured_at)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (snapshot_id, item.provider, item.currency, item.amount, captured_at),
                )
            conn.commit()
            cur.close()

    def latest_snapshot(self) -> PortfolioSnapshot | None:
        if not self.configured:
            return None
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                select h.provider, h.section, h.symbol, h.name, h.quantity, h.currency, h.market_value, h.cost_basis
                from portfolio_holdings h
                join portfolio_snapshots s on s.id = h.snapshot_id
                where s.id in (select distinct on (provider) id from portfolio_snapshots order by provider, captured_at desc)
                order by h.provider, h.symbol
                """
            )
            holdings_rows = cur.fetchall()
            cur.execute(
                """
                select c.provider, c.currency, c.amount
                from portfolio_cash c
                join portfolio_snapshots s on s.id = c.snapshot_id
                where s.id in (select distinct on (provider) id from portfolio_snapshots order by provider, captured_at desc)
                order by c.provider, c.currency
                """
            )
            cash_rows = cur.fetchall()
            cur.close()
        holdings = [Holding(**row) for row in holdings_rows]
        cash = [CashBalance(**row) for row in cash_rows]
        if not holdings and not cash:
            return None
        return PortfolioSnapshot(holdings=holdings, cash=cash)

    def portfolio_evolution(self) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                select date_trunc('day', captured_at) as date, round(sum(value)::numeric, 2) as total_value
                from (
                    select captured_at, market_value as value from portfolio_holdings
                    union all
                    select captured_at, amount as value from portfolio_cash
                ) values_by_day
                group by date
                order by date
                """
            )
            rows = cur.fetchall()
            cur.close()
            return rows

    def version_log(self) -> list[str]:
        if not self.configured:
            return [f"{version} {title}" for version, title in VERSION_ENTRIES]
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("select version, title from version_log order by created_at desc, id desc")
            rows = cur.fetchall()
            cur.close()
        return [f"{row['version']} {row['title']}" for row in rows]

    def add_conversation(self, role: str, content: str) -> None:
        if not self.configured:
            return
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("insert into genai_conversations (role, content) values (%s, %s)", (role, content))
            conn.commit()
            cur.close()

    def conversation(self, limit: int = 12) -> list[dict[str, str]]:
        if not self.configured:
            return []
        with self._connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("select role, content from genai_conversations order by created_at desc limit %s", (limit,))
            rows = cur.fetchall()
            cur.close()
        return list(reversed(rows))
