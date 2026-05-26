import anthropic
import google.generativeai as genai_google
from openai import OpenAI

from app.models import DashboardData
from app.settings import Settings


class GenAIService:
    def __init__(self, settings: Settings):
        self.settings = settings

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
        return await self.chat(dashboard, "Generate concise portfolio insights, risks, diversification observations, and non-personalized recommendations.")

    async def chat(self, dashboard: DashboardData, message: str) -> str:
        if not self.configured:
            return "GenAI is disabled or missing an API key. Configure GENAI_PROVIDER and the matching API key in your environment."
        prompt = self._prompt(dashboard, message)
        if self.settings.genai_provider == "google":
            return self._google(prompt)
        if self.settings.genai_provider == "openai":
            return self._openai(prompt)
        if self.settings.genai_provider == "anthropic":
            return self._anthropic(prompt)
        return "No GenAI provider selected."

    def _prompt(self, dashboard: DashboardData, user_message: str) -> str:
        return f"""
You are an investment portfolio analysis assistant. Do not claim to be a licensed financial advisor. Provide educational, risk-aware, non-guaranteed analysis. Do not recommend illegal, leveraged, or unsuitable actions. Ask for missing information when needed.

Investor profile: {self.settings.investor_profile}
Objectives: {self.settings.investment_objectives}
Risk tolerance: {self.settings.risk_tolerance}
Investment horizon: {self.settings.investment_horizon}
Display currency: {dashboard.display_currency}
Total holdings value: {dashboard.total_holdings_value}
Total cash value: {dashboard.total_cash_value}
By section: {dashboard.by_section}
By provider: {dashboard.by_provider}
Holdings: {[item.model_dump() for item in dashboard.holdings]}
Cash: {[item.model_dump() for item in dashboard.cash]}

User request: {user_message}
""".strip()

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
