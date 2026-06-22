from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HIFY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hify:hify@localhost:5432/hify"
    database_echo: bool = False
    enable_development_header_auth: bool = False
