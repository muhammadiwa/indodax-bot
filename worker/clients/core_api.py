from __future__ import annotations

from typing import Any

import httpx

from worker.config import get_settings


class CoreAPIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(base_url=str(settings.core_api_base_url), timeout=10.0)
        self._internal_token = settings.core_api_internal_token

    def _headers(self, internal: bool) -> dict[str, str]:
        if internal and self._internal_token:
            return {"X-Internal-Token": self._internal_token}
        return {}

    async def post(
        self, path: str, payload: dict[str, Any], *, internal: bool = False
    ) -> dict[str, Any]:
        response = await self._client.post(
            path, json=payload, headers=self._headers(internal)
        )
        response.raise_for_status()
        return response.json()

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        internal: bool = False,
    ) -> dict[str, Any]:
        response = await self._client.get(
            path, params=params, headers=self._headers(internal)
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()


core_api_client = CoreAPIClient()
