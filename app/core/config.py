from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "journal api"
    app_version: str = "0.1.0"
    app_description: str = "A private journaling API."
    environment: str = "development"
    database_url: str


@lru_cache
def get_settings():
    return Settings()
