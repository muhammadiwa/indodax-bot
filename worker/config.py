from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    core_api_base_url: AnyUrl
    redis_url: AnyUrl
    log_level: str = "INFO"
    scheduler_timezone: str = "Asia/Jakarta"
    worker_poll_interval_seconds: int = 30
    core_api_internal_token: str | None = None
    price_feed_ws_url: AnyUrl | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
