from app.settings import Settings


class RuntimeConfig:
    def __init__(self, settings: Settings, values: dict[str, str]):
        self.app_env = settings.app_env
        self.app_secret_key = settings.app_secret_key
        self.database_url = settings.database_url
        self.supabase_db_url = settings.supabase_db_url
        self.default_display_currency = values.get("default_display_currency") or settings.default_display_currency
        self.investor_profile = values.get("investor_profile") or settings.investor_profile
        self.investment_objectives = values.get("investment_objectives") or settings.investment_objectives
        self.risk_tolerance = values.get("risk_tolerance") or settings.risk_tolerance
        self.investment_horizon = values.get("investment_horizon") or settings.investment_horizon
        self.binance_api_key = values.get("binance_api_key") or settings.binance_api_key
        self.binance_api_secret = values.get("binance_api_secret") or settings.binance_api_secret
        self.binance_base_url = values.get("binance_base_url") or settings.binance_base_url
        self.genai_provider = values.get("genai_provider") or settings.genai_provider
        self.genai_model = values.get("genai_model") or settings.genai_model
        self.google_api_key = values.get("google_api_key") or settings.google_api_key
        self.openai_api_key = values.get("openai_api_key") or settings.openai_api_key
        self.anthropic_api_key = values.get("anthropic_api_key") or settings.anthropic_api_key
        self.exchangerate_host_url = values.get("exchangerate_host_url") or settings.exchangerate_host_url
        self.asset_insight_prompt = values.get("asset_insight_prompt", "")
        self.asset_macro_prompt = values.get("asset_macro_prompt", "")
        self.portfolio_insight_prompt = values.get("portfolio_insight_prompt", "")
        self.asset_compare_prompt = values.get("asset_compare_prompt", "")
        self.chat_extra_context = values.get("chat_extra_context", "")
