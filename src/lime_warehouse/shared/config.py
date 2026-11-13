from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./lime_warehouse.db"
    mango_auth_url: str = "http://localhost:8003"
    mango_auth_app: str = "erp"  # token `aud`; stock permissions live in the erp app
    permission_ttl: float = 10.0
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
