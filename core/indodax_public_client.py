from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx


class IndodaxPublicClient:
    BASE_URL = "https://indodax.com/api"

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=timeout)
        self._lock = asyncio.Lock()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def _fetch(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def get_ticker(self, pair: str, *, cache_ttl: float = 5.0) -> dict[str, Any]:
        key = f"ticker:{pair}"
        async with self._lock:
            cached = self._cache.get(key)
            if cached:
                ts, data = cached
                if asyncio.get_event_loop().time() - ts < cache_ttl:
                    return data
        data = await self._fetch(f"ticker/{pair}")
        async with self._lock:
            self._cache[key] = (asyncio.get_event_loop().time(), data)
        return data

    async def get_order_book(
        self,
        pair: str,
        *,
        cache_ttl: float = 2.0,
        depth: int | None = None,
    ) -> dict[str, Any]:
        params: Optional[dict[str, Any]] = None
        if depth:
            params = {"depth": depth}
        key = f"order_book:{pair}:{depth or 'full'}"
        async with self._lock:
            cached = self._cache.get(key)
            if cached:
                ts, data = cached
                if asyncio.get_event_loop().time() - ts < cache_ttl:
                    return data
        data = await self._fetch(f"depth/{pair}", params=params)
        async with self._lock:
            self._cache[key] = (asyncio.get_event_loop().time(), data)
        return data

    async def get_tickers(self, *, cache_ttl: float = 5.0) -> dict[str, Any]:
        key = "tickers"
        async with self._lock:
            cached = self._cache.get(key)
            if cached:
                ts, data = cached
                if asyncio.get_event_loop().time() - ts < cache_ttl:
                    return data
        data = await self._fetch("ticker_all")
        async with self._lock:
            self._cache[key] = (asyncio.get_event_loop().time(), data)
        return data

    async def close(self) -> None:
        await self._client.aclose()


public_client = IndodaxPublicClient()
