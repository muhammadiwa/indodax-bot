import asyncio
import logging
from typing import Any

import httpx
import pendulum

from worker.clients.core_api import core_api_client
from worker.config import get_settings
from worker.utils.notifications import send_notification
from worker.utils.safety import ensure_trading_active, trigger_deadman

logger = logging.getLogger(__name__)


async def _should_run(strategy: dict[str, Any], now: pendulum.DateTime) -> bool:
    config = strategy.get("config_json", {})
    interval = config.get("interval", "daily")
    execution_time = config.get("execution_time", "00:00")
    hour, minute = map(int, execution_time.split(":"))
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < scheduled:
        return False
    max_runs = config.get("max_runs")
    if max_runs is not None:
        count_response = await core_api_client.get(
            f"/api/strategies/{strategy['id']}/executions/count",
            internal=True,
        )
        if count_response.get("data", 0) >= max_runs:
            return False
    last_execution_response = await core_api_client.get(
        f"/api/strategies/{strategy['id']}/executions/last",
        internal=True,
    )
    last_data = last_execution_response.get("data")
    if not last_data:
        return True
    last_run_raw = last_data.get("run_at") or last_data.get("created_at")
    if not last_run_raw:
        return True
    last_run = pendulum.parse(str(last_run_raw))
    if interval == "daily":
        return last_run < scheduled.subtract(days=1)
    if interval == "weekly":
        return last_run < scheduled.subtract(weeks=1)
    if interval == "hourly":
        return now.subtract(hours=1) >= last_run
    return False


async def run_dca_strategies() -> None:
    settings = get_settings()
    now = pendulum.now(settings.scheduler_timezone)
    if not await ensure_trading_active():
        return
    response = await core_api_client.get(
        "/api/strategies/active",
        {"strategy_type": "dca"},
        internal=True,
    )
    strategies = response.get("data", [])
    for strategy in strategies:
        try:
            if not await _should_run(strategy, now):
                continue
            config = strategy.get("config_json", {})
            amount_value = float(config.get("amount", 0) or 0)
            if amount_value <= 0:
                logger.warning("Konfigurasi DCA tidak memiliki nominal valid", extra={"strategy_id": strategy["id"]})
                continue
            payload = {
                "telegram_id": strategy["telegram_id"],
                "pair": config.get("pair", strategy.get("pair")),
                "side": "buy",
                "type": "market",
                "amount": amount_value,
                "is_strategy_order": True,
                "strategy_id": strategy["id"],
            }
            order_response = await core_api_client.post(
                "/api/orders", payload, internal=True
            )
            await core_api_client.post(
                f"/api/strategies/{strategy['id']}/executions",
                {
                    "user_id": strategy["user_id"],
                    "status": "success" if order_response.get("success") else "failed",
                    "detail": {
                        "order_response": order_response,
                        "run_at": now.to_iso8601_string(),
                    },
                },
                internal=True,
            )
            await send_notification(
                strategy["telegram_id"],
                (
                    "Strategi DCA dieksekusi\n"
                    f"Pair: {payload['pair']}\nNominal: {payload['amount']}\n"
                    f"Waktu: {now.to_iso8601_string()}"
                ),
                event_type="strategy_dca_execution",
            )
            logger.info("DCA dijalankan", extra={"strategy_id": strategy["id"]})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gagal menjalankan strategi DCA", extra={"strategy_id": strategy.get("id")})
            await core_api_client.post(
                f"/api/strategies/{strategy['id']}/executions",
                {
                    "user_id": strategy["user_id"],
                    "status": "failed",
                    "detail": {"error": str(exc)},
                },
                internal=True,
            )
            await send_notification(
                strategy["telegram_id"],
                (
                    "Strategi DCA gagal dieksekusi: {error}".format(error=str(exc))
                ),
                event_type="strategy_dca_failed",
            )
            if isinstance(exc, (httpx.HTTPError, asyncio.TimeoutError)):
                await trigger_deadman("Kesalahan komunikasi dengan Indodax", "dca")
