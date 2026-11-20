import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Nova Assistant Backend"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://nova:nova@localhost:5432/nova"
    database_url_sync: str = "postgresql+psycopg://nova:nova@localhost:5432/nova"
    redis_url: str = "redis://localhost:6379/0"

    jwt_private_key_path: str = "secrets/jwt_private.pem"
    jwt_public_key_path: str = "secrets/jwt_public.pem"
    jwt_issuer: str = "nova-backapp"
    jwt_user_audience: str = "nova-user"
    jwt_device_audience: str = "nova-device"
    access_token_ttl_seconds: int = 900

    firebase_credentials_path: str | None = None
    firebase_credentials_json: str | None = None
    fcm_enabled: bool = True

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    docs_enabled: bool = True
    rate_limit_per_minute: int = 10
    sync_default_limit: int = 100
    sync_max_limit: int = 500
    scheduler_timezone: str = "UTC"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(parsed, list):
                        return parsed
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
