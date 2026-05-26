import csv
import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.models import AssetSection, CashBalance, Holding, PortfolioSnapshot
from app.settings import Settings


class BinanceProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.binance_api_key and self.settings.binance_api_secret)

    async def fetch(self) -> PortfolioSnapshot:
        if not self.configured:
            return PortfolioSnapshot()
        balances = await self._signed_get("/api/v3/account")
        tickers = await self._public_get("/api/v3/ticker/price")
        price_by_symbol = {item["symbol"]: float(item["price"]) for item in tickers if "symbol" in item and "price" in item}
        holdings: list[Holding] = []
        cash: list[CashBalance] = []
        for balance in balances.get("balances", []):
            asset = balance.get("asset", "")
            free = float(balance.get("free", 0) or 0)
            locked = float(balance.get("locked", 0) or 0)
            quantity = free + locked
            if quantity <= 0:
                continue
            if asset in {"EUR", "USD", "USDT", "USDC"}:
                cash.append(CashBalance(provider="Binance", currency="USD" if asset in {"USDT", "USDC"} else asset, amount=quantity))
                continue
            quote_symbol = f"{asset}USDT"
            price = price_by_symbol.get(quote_symbol, 0)
            holdings.append(
                Holding(
                    provider="Binance",
                    section=AssetSection.cryptos,
                    symbol=asset,
                    name=asset,
                    quantity=quantity,
                    currency="USD",
                    market_value=round(quantity * price, 2),
                )
            )
        return PortfolioSnapshot(holdings=holdings, cash=cash)

    async def _public_get(self, path: str) -> list[dict]:
        async with httpx.AsyncClient(base_url=self.settings.binance_base_url, timeout=12) as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.json()

    async def _signed_get(self, path: str) -> dict:
        params = {"timestamp": int(time.time() * 1000)}
        query = urlencode(params)
        signature = hmac.new(self.settings.binance_api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        headers = {"X-MBX-APIKEY": self.settings.binance_api_key}
        async with httpx.AsyncClient(base_url=self.settings.binance_base_url, timeout=12) as client:
            response = await client.get(f"{path}?{query}&signature={signature}", headers=headers)
            response.raise_for_status()
            return response.json()


class DegiroCsvProvider:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, report_type: str, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        path = self.data_dir / f"degiro_{report_type}_{safe_name}"
        path.write_bytes(content)
        return path

    def fetch(self) -> PortfolioSnapshot:
        holdings: list[Holding] = []
        cash: list[CashBalance] = []
        for path in self.data_dir.glob("degiro_portfolio_*.csv"):
            holdings.extend(self._parse_portfolio(path))
        for path in self.data_dir.glob("degiro_account_*.csv"):
            cash.extend(self._parse_account(path))
        return PortfolioSnapshot(holdings=holdings, cash=cash)

    def _parse_portfolio(self, path: Path) -> list[Holding]:
        rows = self._read_rows(path)
        parsed: list[Holding] = []
        for row in rows:
            symbol = self._first(row, "Symbol", "ISIN", "Product", "Name")
            name = self._first(row, "Product", "Name", "Description", default=symbol)
            value = self._number(self._first(row, "Value", "Market Value", "Value in EUR", "Total", default="0"))
            quantity = self._number(self._first(row, "Quantity", "Number", "Amount", default="0"))
            currency = self._first(row, "Currency", "Valuta", default="EUR").upper()
            product_type = self._first(row, "Type", "Product Type", "Category", default="Shares").lower()
            section = AssetSection.funds if "fund" in product_type or "etf" in product_type else AssetSection.shares
            if symbol and value:
                parsed.append(Holding(provider="DEGIRO", section=section, symbol=symbol, name=name, quantity=quantity, currency=currency, market_value=value))
        return parsed

    def _parse_account(self, path: Path) -> list[CashBalance]:
        rows = self._read_rows(path)
        balances: dict[str, float] = {}
        for row in rows:
            currency = self._first(row, "Currency", "Valuta", default="EUR").upper()
            amount = self._number(self._first(row, "Balance", "Amount", "Change", "Mutatie", default="0"))
            balances[currency] = balances.get(currency, 0) + amount
        return [CashBalance(provider="DEGIRO", currency=currency, amount=round(amount, 2)) for currency, amount in balances.items() if amount]

    def _read_rows(self, path: Path) -> list[dict[str, str]]:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        sample = text[:2048]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
        return list(csv.DictReader(text.splitlines(), dialect=dialect))

    def _first(self, row: dict[str, str], *names: str, default: str = "") -> str:
        normalized = {key.strip().lower(): value for key, value in row.items() if key}
        for name in names:
            value = normalized.get(name.lower())
            if value not in (None, ""):
                return value.strip()
        return default

    def _number(self, value: str) -> float:
        cleaned = value.replace("€", "").replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
