from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    telegram_bot_token: str
    core_api_base_url: AnyUrl
    redis_url: AnyUrl = "redis://redis:6379/1"
    log_level: str = "INFO"
    bot_internal_host: str = "0.0.0.0"
    bot_internal_port: int = 8080
    user_token_ttl_seconds: int = 86_400
    user_token_refresh_threshold_seconds: int = 3_600
    app_secret_key: str = "change-me-super-secret-32bytes"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
