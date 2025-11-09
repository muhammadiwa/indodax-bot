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


async def run_grid_strategies() -> None:
    settings = get_settings()
    now = pendulum.now(settings.scheduler_timezone)
    if not await ensure_trading_active():
        return
    response = await core_api_client.get(
        "/api/strategies/active",
        {"strategy_type": "grid"},
        internal=True,
    )
    strategies = response.get("data", [])
    for strategy in strategies:
        config: dict[str, Any] = strategy.get("config_json", {})
        lower = float(config.get("lower_price", 0))
        upper = float(config.get("upper_price", 0))
        grid_count = int(config.get("grid_count", 0))
        size = float(config.get("order_size", 0))
        if not lower or not upper or grid_count <= 0:
            continue
        step = (upper - lower) / grid_count
        price_levels = [lower + step * i for i in range(grid_count + 1)]
        midpoint = (lower + upper) / 2
        try:
            open_orders_resp = await core_api_client.get(
                "/api/orders/open",
                {
                    "telegram_id": strategy["telegram_id"],
                    "pair": strategy["pair"],
                    "strategy_id": strategy["id"],
                },
                internal=True,
            )
            open_orders = open_orders_resp.get("data", [])
            tolerance = 1.0
            target_levels = [
                {
                    "price": price,
                    "side": "buy" if price <= midpoint else "sell",
                }
                for price in price_levels
            ]

            active_orders: list[dict[str, Any]] = []
            stale_orders: list[dict[str, Any]] = []
            for order in open_orders:
                if not order.get("is_strategy_order") or order.get("strategy_id") != strategy["id"]:
                    continue
                order_price = order.get("price")
                order_side = order.get("side")
                if order_price is None or order_side not in {"buy", "sell"}:
                    stale_orders.append(order)
                    continue
                price_value = float(order_price)
                matched = next(
                    (
                        level
                        for level in target_levels
                        if level["side"] == order_side
                        and abs(level["price"] - price_value) <= tolerance
                    ),
                    None,
                )
                if matched:
                    active_orders.append(order)
                else:
                    stale_orders.append(order)

            for order in stale_orders:
                order_id = order.get("id")
                if not order_id:
                    continue
                try:
                    await core_api_client.post(
                        f"/api/orders/{order_id}/cancel",
                        {"telegram_id": strategy["telegram_id"]},
                        internal=True,
                    )
                    logger.info(
                        "grid.cancelled_stale_order",
                        extra={
                            "strategy_id": strategy["id"],
                            "order_id": order_id,
                            "price": order.get("price"),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Gagal membatalkan order grid kadaluarsa",
                        extra={
                            "strategy_id": strategy.get("id"),
                            "order_id": order_id,
                            "error": str(exc),
                        },
                    )

            effective_orders = list(active_orders)
            for price in price_levels:
                side = "buy" if price <= midpoint else "sell"
                already_exists = any(
                    order.get("side") == side
                    and order.get("price") is not None
                    and abs(float(order.get("price")) - price) <= tolerance
                    for order in effective_orders
                )
                if already_exists:
                    continue
                payload = {
                    "telegram_id": strategy["telegram_id"],
                    "pair": strategy["pair"],
                    "side": side,
                    "type": "limit",
                    "amount": size,
                    "price": price,
                    "is_strategy_order": True,
                    "strategy_id": strategy["id"],
                }
                await core_api_client.post(
                    "/api/orders", payload, internal=True
                )
                effective_orders.append({"side": side, "price": price})

            await core_api_client.post(
                f"/api/strategies/{strategy['id']}/executions",
                {
                    "user_id": strategy["user_id"],
                    "status": "success",
                    "detail": {
                        "grids": price_levels,
                        "timestamp": now.to_iso8601_string(),
                        "canceled_orders": [order.get("id") for order in stale_orders],
                    },
                },
                internal=True,
            )
            await send_notification(
                strategy["telegram_id"],
                (
                    "Strategi grid diperbarui\n"
                    f"Pair: {strategy['pair']}\nLevel: {len(price_levels)}\n"
                    f"Rentang: {lower:,.0f} - {upper:,.0f}"
                ),
                event_type="strategy_grid_execution",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gagal menjalankan grid", extra={"strategy_id": strategy.get("id")})
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
                "Penempatan grid gagal: {error}".format(error=str(exc)),
                event_type="strategy_grid_failed",
            )
            if isinstance(exc, (httpx.HTTPError, asyncio.TimeoutError)):
                await trigger_deadman("Kesalahan komunikasi dengan Indodax", "grid")
