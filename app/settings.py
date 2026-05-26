from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default .env path (only loaded when file exists locally).
# On Render and other platforms, environment variables take priority.
_DEFAULT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_DEFAULT_ENV_FILE_PATH = str(_DEFAULT_ENV_FILE) if _DEFAULT_ENV_FILE.exists() else None

# Optional override path set from the environment page.
_CUSTOM_ENV_FILE: str | None = None


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
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")


@lru_cache
def _get_settings_impl() -> Settings:
    env_file = _CUSTOM_ENV_FILE or _DEFAULT_ENV_FILE_PATH
    if env_file:
        return Settings(_env_file=env_file, _env_file_encoding="utf-8")
    return Settings()


def get_settings() -> Settings:
    return _get_settings_impl()


def set_env_file(path: str | None) -> None:
    global _CUSTOM_ENV_FILE
    _CUSTOM_ENV_FILE = path
    _get_settings_impl.cache_clear()
