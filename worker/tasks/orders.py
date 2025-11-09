import asyncio
import asyncio
import logging

import httpx

from worker.clients.core_api import core_api_client
from worker.utils.safety import ensure_trading_active, trigger_deadman

logger = logging.getLogger(__name__)


async def monitor_orders() -> None:
    if not await ensure_trading_active():
        return
    try:
        response = await core_api_client.post(
            "/api/orders/sync-status",
            {"telegram_ids": None},
            internal=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gagal sinkronisasi status order", exc_info=exc)
        if isinstance(exc, (httpx.HTTPError, asyncio.TimeoutError)):
            await trigger_deadman("Sinkronisasi order gagal", "order-monitor")
        return
    data = response.get("data", {})
    updated = data.get("updated", 0)
    if updated:
        logger.info("Order status diperbarui", extra={"jumlah": updated})
