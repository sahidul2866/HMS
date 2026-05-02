from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "https://sahidul2866.github.io",
]
DEFAULT_FRONTEND_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="MediProfit API", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(default="development", alias="APP_ENV")
    debug: bool | str = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    database_url: str = Field(alias="DATABASE_URL")
    frontend_origins: str | list[str] = Field(default_factory=lambda: DEFAULT_FRONTEND_ORIGINS.copy(), alias="FRONTEND_ORIGINS")
    frontend_origin_regex: str = Field(default=DEFAULT_FRONTEND_ORIGIN_REGEX, alias="FRONTEND_ORIGIN_REGEX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    auto_db_bootstrap: bool | str = Field(default=True, alias="AUTO_DB_BOOTSTRAP")
    auto_seed_sample_data: bool | str = Field(default=False, alias="AUTO_SEED_SAMPLE_DATA")
    max_patients_per_mobile: int = Field(default=5, alias="MAX_PATIENTS_PER_MOBILE")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    patient_bot_max_gemini_calls_per_day: int = Field(default=5, alias="PATIENT_BOT_MAX_GEMINI_CALLS_PER_DAY")

    def model_post_init(self, __context: object) -> None:
        self.debug = self._normalize_bool(self.debug, default=False)
        self.auto_db_bootstrap = self._normalize_bool(self.auto_db_bootstrap, default=True)
        self.auto_seed_sample_data = self._normalize_bool(self.auto_seed_sample_data, default=False)
        self.database_url = self._normalize_database_url(self.database_url)
        self.secret_key = self.secret_key.strip().strip("\"'")
        self.log_level = self.log_level.strip().strip("\"'")
        self.gemini_model = self.gemini_model.strip().strip("\"'")
        if self.gemini_api_key:
            self.gemini_api_key = self.gemini_api_key.strip().strip("\"'")
        if isinstance(self.frontend_origins, str):
            normalized = self.frontend_origins.strip().strip("\"'")
            self.frontend_origins = [item.strip().strip("\"'") for item in normalized.split(",") if item.strip()]
        self.frontend_origin_regex = self.frontend_origin_regex.strip().strip("\"'")

    @staticmethod
    def _normalize_bool(value: bool | str, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        normalized = value.strip().strip("\"'").lower()
        if normalized in {"1", "true", "yes", "y", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "release", "prod", "production"}:
            return False
        return default

    @staticmethod
    def _normalize_database_url(value: str) -> str:
        normalized = value.strip().strip("\"'")
        if normalized.startswith("DATABASE_URL="):
            normalized = normalized.split("=", 1)[1].strip().strip("\"'")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
