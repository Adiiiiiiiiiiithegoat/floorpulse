from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-insecure-secret-change-me-0123456789"  # noqa: S105 - rejected in prod


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FP_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///./floorpulse.db"
    secret_key: str = _DEV_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False
    max_request_bytes: int = 12 * 1024 * 1024
    log_level: str = "INFO"
    log_json: bool = True
    sentry_dsn: str | None = None
    scheduler_enabled: bool = True
    upload_dir: str = "./uploads"
    public_base_url: str = "http://localhost:5173"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "FloorPulse <no-reply@floorpulse.local>"
    # PIN brute-force protection
    pin_max_failures: int = 5
    pin_lockout_minutes: int = 5

    @model_validator(mode="after")
    def _check_prod(self) -> "Settings":
        if self.env == "prod" and (self.secret_key == _DEV_SECRET or len(self.secret_key) < 32):
            raise ValueError("FP_SECRET_KEY must be set to a random value of at least 32 chars in prod")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
