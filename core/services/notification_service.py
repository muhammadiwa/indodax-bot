from typing import Any

import httpx

from core.config import get_settings


class NotificationService:
    def __init__(self) -> None:
        settings = get_settings()
        self._webhook_url = (
            str(settings.bot_internal_webhook) if settings.bot_internal_webhook else None
        )
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None or self._client.is_closed:  # type: ignore[attr-defined]
            self._client = httpx.AsyncClient(timeout=10.0)

    async def notify(self, payload: dict[str, Any]) -> None:
        if not self._webhook_url:
            return
        if self._client is None or self._client.is_closed:  # type: ignore[attr-defined]
            await self.start()
        response = await self._client.post(self._webhook_url, json=payload)
        response.raise_for_status()

    async def stop(self) -> None:
        if self._client and not self._client.is_closed:  # type: ignore[attr-defined]
            await self._client.aclose()


notification_service = NotificationService()
