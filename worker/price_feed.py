from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

from worker.clients.core_api import core_api_client
from worker.config import get_settings

logger = logging.getLogger(__name__)


class PriceFeed:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: dict[str, tuple[float, float]] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._settings.price_feed_ws_url and not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover
                pass
            self._task = None

    async def _run(self) -> None:
        ws_url = self._settings.price_feed_ws_url
        if not ws_url:
            return
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(str(ws_url), heartbeat=25) as ws:
                        logger.info("Terhubung ke WebSocket harga")
                        async for message in ws:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                self._handle_message(message.data)
                            elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as exc:  # noqa: BLE001
                logger.exception("Koneksi WebSocket harga terputus", exc_info=exc)
                await asyncio.sleep(5)

    def _handle_message(self, raw: str) -> None:
        if not raw.startswith("42"):
            return
        try:
            payload = json.loads(raw[2:])
        except json.JSONDecodeError:
            return
        if not isinstance(payload, list) or len(payload) < 2:
            return
        event, data = payload[0], payload[1]
        if event not in {"market:summary", "market:update"}:
            return
        tickers: list[dict[str, Any]]
        if isinstance(data, dict) and "tickers" in data:
            tickers = data.get("tickers", [])
        elif isinstance(data, list):
            tickers = data
        else:
            tickers = []
        for ticker in tickers:
            pair = ticker.get("pair") or ticker.get("symbol")
            last = ticker.get("last") or ticker.get("last_price")
            if not pair or last is None:
                continue
            try:
                price_value = float(last)
            except (TypeError, ValueError):
                continue
            key = str(pair).upper()
            self._cache[key] = (price_value, time.time())

    async def get_price(self, pair: str) -> float | None:
        key = pair.upper()
        cached = self._cache.get(key)
        now = time.time()
        if cached and now - cached[1] < 5:
            return cached[0]
        try:
            response = await core_api_client.get(f"/api/market/price/{pair}")
        except Exception:  # noqa: BLE001
            return cached[0] if cached else None
        price = response.get("data", {}).get("price")
        if price is not None:
            try:
                price_value = float(price)
            except (TypeError, ValueError):
                return None
            self._cache[key] = (price_value, now)
            return price_value
        return None


price_feed = PriceFeed()
