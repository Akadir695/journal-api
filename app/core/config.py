from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Journal API"
    app_version: str = "0.1.0"
    app_description: str = (
        "A private journaling API. Entries with tags, moods and full-text search, "
        "per-user statistics, background exports, and image attachments uploaded "
        "directly to blob storage.\n\n"
        "All endpoints require a verified account. Authenticate with "
        "`POST /api/v1/auth/login` and send the access token as a bearer token."
    )
    database_url: str
    test_database_url: str | None = None
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]
    test_redis_url: str = "redis://localhost:6379/15"
    cache_ttl_seconds: int = 300
    export_dir: str = "exports"
    azure_storage_connection_string: str
    azure_storage_container: str = "attachments"
    base_url: str = "http://localhost:8000"
    resend_api_key: str | None = None
    email_from: str = "onboarding@resend.dev"
    environment: str = "development"
  

@lru_cache
def get_settings():
    return Settings()
