import asyncio
from typing import Optional

import redis.asyncio as redis

from core.config import get_settings

_settings = get_settings()


class NonceManager:
    def __init__(self) -> None:
        self._client = redis.from_url(str(_settings.redis_url), decode_responses=True)
        self._lock = asyncio.Lock()

    async def get_next_nonce(self, user_id: int) -> int:
        key = f"nonce:{user_id}"
        async with self._lock:
            value = await self._client.incr(key)
            if value == 1:
                await self._client.expire(key, 3600 * 24)
        return value

    async def set_nonce(self, user_id: int, value: int) -> None:
        key = f"nonce:{user_id}"
        await self._client.set(key, value, ex=3600 * 24)


nonce_manager = NonceManager()
