from __future__ import annotations

import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

import httpx

from core.utils.nonce import nonce_manager


class IndodaxPrivateClientError(Exception):
    pass


class IndodaxPrivateClient:
    BASE_URL = "https://indodax.com/tapi"

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=timeout)

    async def _sign(self, body: dict[str, Any], api_secret: str) -> str:
        payload = urlencode(body)
        return hmac.new(
            api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

    async def _request(
        self,
        method: str,
        body: dict[str, Any],
        api_key: str,
        api_secret: str,
    ) -> dict[str, Any]:
        body.update({"method": method})
        payload = urlencode(body)
        headers = {
            "Key": api_key,
            "Sign": await self._sign(body, api_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = await self._client.post("", content=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise IndodaxPrivateClientError(data.get("error", "Unknown error"))
        return data

    async def call(
        self,
        user_id: int,
        method: str,
        params: dict[str, Any],
        api_key: str,
        api_secret: str,
    ) -> dict[str, Any]:
        nonce = await nonce_manager.get_next_nonce(user_id)
        body = {"nonce": nonce}
        body.update(params)
        return await self._request(method, body, api_key, api_secret)

    async def close(self) -> None:
        await self._client.aclose()


private_client = IndodaxPrivateClient()
