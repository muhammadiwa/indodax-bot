from __future__ import annotations

from typing import Any

from bot.services.api_client import core_api_client


async def get_top_pairs(limit: int = 6) -> list[str]:
    response = await core_api_client.get("/api/market/tickers")
    tickers: dict[str, Any] = response.get("data", {}).get("tickers", {})
    def volume_value(item: tuple[str, Any]) -> float:
        data = item[1] or {}
        candidates = [
            data.get("vol_idr"),
            data.get("vol_idr_rp"),
            data.get("vol_idr2"),
            data.get("volume"),
        ]
        for candidate in candidates:
            try:
                return float(candidate)
            except (TypeError, ValueError):
                continue
        return 0.0

    sorted_pairs = sorted(tickers.items(), key=volume_value, reverse=True)
    return [pair.upper() for pair, _ in sorted_pairs[:limit]]
