from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from core.config import get_settings


class SafetyService:
    def __init__(self) -> None:
        settings = get_settings()
        self._redis = redis.from_url(str(settings.redis_url), decode_responses=True)
        self._key = "safety:deadman"

    async def pause(self, *, reason: str, source: str | None = None) -> dict[str, Any]:
        data = {
            "paused": True,
            "reason": reason,
            "source": source or "unknown",
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self._redis.set(self._key, json.dumps(data))
        return data

    async def resume(self) -> dict[str, Any]:
        data = {
            "paused": False,
            "reason": None,
            "source": None,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self._redis.set(self._key, json.dumps(data))
        return data

    async def get_status(self) -> dict[str, Any]:
        raw = await self._redis.get(self._key)
        if not raw:
            return {
                "paused": False,
                "reason": None,
                "source": None,
                "updated_at": None,
            }
        data = json.loads(raw)
        return {
            "paused": bool(data.get("paused")),
            "reason": data.get("reason"),
            "source": data.get("source"),
            "updated_at": data.get("updated_at"),
        }


safety_service = SafetyService()
