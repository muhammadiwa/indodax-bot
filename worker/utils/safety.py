from __future__ import annotations

import logging

from worker.clients.core_api import core_api_client

logger = logging.getLogger(__name__)


async def get_safety_status() -> dict:
    response = await core_api_client.get("/api/system/status")
    return response.get("data", {})


async def ensure_trading_active() -> bool:
    status = await get_safety_status()
    if status.get("paused"):
        logger.warning("Strategi dijeda oleh dead-man switch", extra={"reason": status.get("reason")})
        return False
    return True


async def trigger_deadman(reason: str, source: str) -> None:
    await core_api_client.post(
        "/api/system/pause",
        {"reason": reason, "source": source},
        internal=True,
    )
