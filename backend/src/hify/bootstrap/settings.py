from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HIFY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hify:hify@localhost:5432/hify"
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend_url: str | None = None
    celery_task_soft_time_limit_seconds: int = 300
    celery_task_hard_time_limit_seconds: int = 360
    celery_visibility_timeout_seconds: int = 3600
    provider_credential_encryption_key: str | None = None
    provider_credential_key_version: int = 1
    auth_cookie_name: str = "hify_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_session_ttl_seconds: int = 604800
    auth_dev_login_enabled: bool = False
    auth_oidc_enabled: bool = False
