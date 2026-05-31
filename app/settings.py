from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default .env path (only loaded when file exists locally).
# On Render and other platforms, environment variables take priority.
_DEFAULT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_DEFAULT_ENV_FILE_PATH = str(_DEFAULT_ENV_FILE) if _DEFAULT_ENV_FILE.exists() else None


class Settings(BaseSettings):
    app_env: str = "local"
    app_secret_key: str = Field(default="change-me", repr=False)
    database_url: str | None = Field(default=None, repr=False)
    supabase_db_url: str | None = Field(default=None, repr=False)
    default_display_currency: Literal["NATIVE", "EUR", "USD"] = "EUR"

    investor_profile: str = "Long-term investor focused on diversified growth."
    investment_objectives: str = "Capital appreciation and diversification."
    risk_tolerance: str = "moderate"
    investment_horizon: str = "10+ years"

    binance_api_key: str | None = Field(default=None, repr=False)
    binance_api_secret: str | None = Field(default=None, repr=False)
    binance_base_url: str = "https://api.binance.com"

    genai_provider: Literal["disabled", "google", "openai", "anthropic"] = "disabled"
    genai_model: str | None = None
    google_api_key: str | None = Field(default=None, repr=False)
    openai_api_key: str | None = Field(default=None, repr=False)
    anthropic_api_key: str | None = Field(default=None, repr=False)

    exchangerate_host_url: str = "https://api.exchangerate.host"
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    @property
    def available_genai_providers(self) -> list[str]:
        providers = []
        if self.google_api_key:
            providers.append("google")
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        return providers


@lru_cache
def _get_settings_impl() -> Settings:
    if _DEFAULT_ENV_FILE_PATH:
        return Settings(_env_file=_DEFAULT_ENV_FILE_PATH, _env_file_encoding="utf-8")
    return Settings()


def get_settings() -> Settings:
    return _get_settings_impl()
