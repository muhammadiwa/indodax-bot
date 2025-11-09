from __future__ import annotations

from typing import Any

import httpx

from bot.config import get_settings


class CoreAPIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(base_url=str(settings.core_api_base_url), timeout=10.0)

    def _headers(self, user_token: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
        return headers

    async def post(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        params: dict[str, Any] | None = None,
        user_token: str | None = None,
    ) -> dict[str, Any]:
        response = await self._client.post(
            path,
            json=payload,
            params=params,
            headers=self._headers(user_token),
        )
        response.raise_for_status()
        return response.json()

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        user_token: str | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(
            path, params=params, headers=self._headers(user_token)
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()


core_api_client = CoreAPIClient()
