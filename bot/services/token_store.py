from __future__ import annotations

from datetime import datetime, timezone

from bot.utils.crypto import (
    TokenEncryptionError,
    decrypt_token_value,
    encrypt_token_value,
)

from redis.asyncio import Redis

from bot.config import get_settings


class TokenStore:
    def __init__(self) -> None:
        settings = get_settings()
        self._redis = Redis.from_url(
            str(settings.redis_url), decode_responses=True
        )
        self._prefix = "user_token"
        self._ttl_seconds = settings.user_token_ttl_seconds
        self._secret_key = settings.app_secret_key

    def _key(self, telegram_id: int) -> str:
        return f"{self._prefix}:{telegram_id}"

    async def set_token(
        self,
        telegram_id: int,
        token: str,
        *,
        expires_at: datetime | None = None,
    ) -> None:
        ttl = self._ttl_seconds
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = int((expires_at - now).total_seconds())
            if delta > 0:
                ttl = delta
        payload = encrypt_token_value(token, self._secret_key)
        await self._redis.set(self._key(telegram_id), payload, ex=max(ttl, 1))

    async def get_token_with_ttl(self, telegram_id: int) -> tuple[str | None, int | None]:
        key = self._key(telegram_id)
        payload = await self._redis.get(key)
        if payload is None:
            return None, None
        ttl = await self._redis.ttl(key)
        try:
            token = decrypt_token_value(payload, self._secret_key)
        except TokenEncryptionError:
            token = payload
            try:
                refreshed_ttl = ttl if ttl and ttl > 0 else self._ttl_seconds
                new_payload = encrypt_token_value(token, self._secret_key)
                await self._redis.set(key, new_payload, ex=max(refreshed_ttl, 1))
            except TokenEncryptionError:
                pass
        if ttl is not None and ttl < 0:
            ttl = None
        return token, ttl

    async def delete_token(self, telegram_id: int) -> None:
        await self._redis.delete(self._key(telegram_id))

    async def close(self) -> None:
        await self._redis.close()
        await self._redis.wait_closed()


token_store = TokenStore()
