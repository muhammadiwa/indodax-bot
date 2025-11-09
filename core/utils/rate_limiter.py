import redis.asyncio as redis

from core.config import get_settings

_settings = get_settings()
_client = redis.from_url(str(_settings.redis_url), decode_responses=True)


async def allow_action(user_id: int, action: str, limit: int, window_seconds: int) -> bool:
    key = f"rate:{user_id}:{action}"
    current = await _client.incr(key)
    if current == 1:
        await _client.expire(key, window_seconds)
    if current > limit:
        return False
    return True
