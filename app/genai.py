import os
from pathlib import Path
from typing import Any

import anthropic
import google.generativeai as genai_google
from openai import OpenAI

from app.models import DashboardData
from app.settings import Settings

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_INSIGHTS_FILE = BASE_DIR / "templates" / "prompt_insights_1.txt"
CONVERSATION_HISTORY: list[dict[str, str]] = []


class GenAIService:
    def __init__(self, settings: Settings, database: Any | None = None):
        self.settings = settings
        self.database = database

    @property
    def configured(self) -> bool:
        if self.settings.genai_provider == "google":
            return bool(self.settings.google_api_key)
        if self.settings.genai_provider == "openai":
            return bool(self.settings.openai_api_key)
        if self.settings.genai_provider == "anthropic":
            return bool(self.settings.anthropic_api_key)
        return False

    async def insights(self, dashboard: DashboardData) -> str:
        return await self.chat(dashboard, "Generate recommendations and insights.", use_insights_prompt=True)

    async def portfolio_insight(self, dashboard: DashboardData) -> str:
        prompt = self.settings.portfolio_insight_prompt.format(portfolio=self._portfolio_block(dashboard), investor_profile=self._investor_profile_block())
        return await self.chat(dashboard, prompt)

    async def asset_insight(self, dashboard: DashboardData, symbol: str) -> str:
        asset = self._asset_block(dashboard, symbol)
        prompt = self.settings.asset_insight_prompt.format(asset=asset, portfolio=self._portfolio_block(dashboard), investor_profile=self._investor_profile_block())
        return await self.chat(dashboard, prompt)

    async def asset_macro(self, dashboard: DashboardData, symbol: str) -> str:
        asset = self._asset_block(dashboard, symbol)
        prompt = self.settings.asset_macro_prompt.format(asset=asset, portfolio=self._portfolio_block(dashboard), investor_profile=self._investor_profile_block())
        return await self.chat(dashboard, prompt)

    async def asset_compare(self, dashboard: DashboardData, symbol: str) -> str:
        asset = self._asset_block(dashboard, symbol)
        prompt = self.settings.asset_compare_prompt.format(asset=asset, portfolio=self._portfolio_block(dashboard), investor_profile=self._investor_profile_block())
        return await self.chat(dashboard, prompt)

    async def chat(self, dashboard: DashboardData, message: str, use_insights_prompt: bool = False) -> str:
        if not self.configured:
            return "GenAI is disabled or missing an API key. Configure GENAI_PROVIDER and the matching API key in your environment."
        prompt = self._prompt(dashboard, message, use_insights_prompt)
        if self.settings.genai_provider == "google":
            answer = self._google(prompt)
        elif self.settings.genai_provider == "openai":
            answer = self._openai(prompt)
        elif self.settings.genai_provider == "anthropic":
            answer = self._anthropic(prompt)
        else:
            return "No GenAI provider selected."
        CONVERSATION_HISTORY.append({"role": "user", "content": message})
        CONVERSATION_HISTORY.append({"role": "assistant", "content": answer})
        if self.database:
            self.database.add_conversation("user", message)
            self.database.add_conversation("assistant", answer)
        return answer

    def _prompt(self, dashboard: DashboardData, user_message: str, use_insights_prompt: bool = False) -> str:
        investor_profile = self._investor_profile_block()
        portfolio = self._portfolio_block(dashboard)
        history = self._conversation_block()
        if use_insights_prompt:
            template = PROMPT_INSIGHTS_FILE.read_text(encoding="utf-8")
            template = template.replace("[PASTE INVESTOR PROFILE HERE]", investor_profile)
            template = template.replace("[PASTE PORTFOLIO HOLDINGS HERE]", portfolio)
            template = template.replace("[PASTE ADDITIONAL CONSTRAINTS, PREFERENCES, OR BENCHMARKS HERE]", "Use the investor variables above. Render environment variables override .env and default settings.")
            return f"{template}\n\n# CONVERSATION CONTEXT\n{history}\n\n# USER REQUEST\n{user_message}".strip()
        return f"""
You are an investment portfolio analysis assistant. Do not claim to be a licensed financial advisor. Provide educational, risk-aware, non-guaranteed analysis. Do not recommend illegal, leveraged, or unsuitable actions. Ask for missing information when needed.

Render environment variables override .env and default settings.

Investor profile:
{investor_profile}

Current portfolio:
{portfolio}

Conversation so far:
{history}

Extra context:
{self.settings.chat_extra_context}

User request: {user_message}
""".strip()

    def _investor_profile_block(self) -> str:
        values = {
            "INVESTOR_PROFILE": self.settings.investor_profile,
            "INVESTMENT_OBJECTIVES": self.settings.investment_objectives,
            "RISK_TOLERANCE": self.settings.risk_tolerance,
            "INVESTMENT_HORIZON": self.settings.investment_horizon,
        }
        investor_terms = ("INVESTOR", "INVESTMENT", "RISK", "HORIZON", "GOAL", "OBJECTIVE", "LIQUIDITY", "COUNTRY", "AGE", "TAX", "CASH", "CONTRIBUTION", "CRYPTO", "BENCHMARK", "PREFERENCE", "TOLERANCE")
        for key, value in os.environ.items():
            if any(term in key.upper() for term in investor_terms):
                values[key] = value
        return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()) if value not in (None, ""))

    def _portfolio_block(self, dashboard: DashboardData) -> str:
        total = dashboard.total_holdings_value + dashboard.total_cash_value
        lines = [
            f"- Display currency: {dashboard.display_currency}",
            f"- Total holdings value: {dashboard.total_holdings_value:.2f} {dashboard.display_currency}",
            f"- Total cash value: {dashboard.total_cash_value:.2f} {dashboard.display_currency}",
            f"- Allocation by section: {dashboard.by_section}",
            f"- Allocation by provider: {dashboard.by_provider}",
            "",
            "Holdings:",
        ]
        for item in dashboard.holdings:
            weight = (item.display_market_value / total * 100) if total else 0
            lines.append(
                f"- {item.section.value} | {item.symbol} | {item.name} | provider: {item.provider} | quantity: {item.quantity} | value: {item.display_market_value:.2f} {item.display_currency} | weight: {weight:.2f}% | currency: {item.currency}"
            )
        lines.append("")
        lines.append("Cash:")
        for item in dashboard.cash:
            weight = (item.display_amount / total * 100) if total else 0
            lines.append(f"- Cash | provider: {item.provider} | currency: {item.currency} | amount: {item.display_amount:.2f} {item.display_currency} | weight: {weight:.2f}%")
        return "\n".join(lines)

    def _conversation_block(self) -> str:
        if self.database:
            rows = self.database.conversation()
            if rows:
                return "\n".join(f"{item['role']}: {item['content']}" for item in rows)
        if not CONVERSATION_HISTORY:
            return "No previous conversation in this app session."
        recent = CONVERSATION_HISTORY[-12:]
        return "\n".join(f"{item['role']}: {item['content']}" for item in recent)

    def _asset_block(self, dashboard: DashboardData, symbol: str) -> str:
        for item in dashboard.holdings:
            if item.symbol == symbol:
                return str(item.model_dump())
        return f"Asset symbol not found in current portfolio: {symbol}"

    def _google(self, prompt: str) -> str:
        genai_google.configure(api_key=self.settings.google_api_key)
        model_name = self.settings.genai_model or "gemini-1.5-flash"
        model = genai_google.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text or "No response from Google model."

    def _openai(self, prompt: str) -> str:
        model_name = self.settings.genai_model or "gpt-4o-mini"
        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content or "No response from OpenAI model."

    def _anthropic(self, prompt: str) -> str:
        model_name = self.settings.genai_model or "claude-3-5-haiku-latest"
        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        response = client.messages.create(model=model_name, max_tokens=1200, messages=[{"role": "user", "content": prompt}])
        return "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text")
