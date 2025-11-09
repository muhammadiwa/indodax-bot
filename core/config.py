from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str
    database_url: AnyUrl
    redis_url: AnyUrl
    core_host: str = "0.0.0.0"
    core_port: int = 8000
    log_level: str = "INFO"
    internal_auth_token: str
    bot_internal_webhook: AnyUrl | None = None
    user_token_ttl_seconds: int = 86_400
    user_token_rotation_threshold_seconds: int = 3_600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
