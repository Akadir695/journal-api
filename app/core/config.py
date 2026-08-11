from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "journal api"
    app_version: str = "0.1.0"
    app_description: str = "A private journaling API."
    environment: str = "development"


@lru_cache
def get_settings():
    return Settings()
