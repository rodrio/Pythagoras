from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only load .env when the file exists locally.
# On Render (and other platforms), environment variables take priority.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_ENV_FILE_PATH = str(_ENV_FILE) if _ENV_FILE.exists() else None


class Settings(BaseSettings):
    app_env: str = "local"
    app_secret_key: str = Field(default="change-me", repr=False)
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

    # pydantic-settings v2: environment variables always override .env file values.
    # When _ENV_FILE_PATH is None (e.g., on Render), only environment variables are used.
    model_config = SettingsConfigDict(env_file=_ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
