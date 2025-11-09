import asyncio
import logging
from typing import Any

import httpx
import pendulum

from worker.clients.core_api import core_api_client
from worker.config import get_settings
from worker.price_feed import price_feed
from worker.utils.notifications import send_notification
from worker.utils.safety import ensure_trading_active, trigger_deadman

logger = logging.getLogger(__name__)


async def monitor_tp_sl() -> None:
    settings = get_settings()
    now = pendulum.now(settings.scheduler_timezone)
    if not await ensure_trading_active():
        return
    response = await core_api_client.get(
        "/api/strategies/active",
        {"strategy_type": "tp_sl"},
        internal=True,
    )
    strategies = response.get("data", [])
    for strategy in strategies:
        config: dict[str, Any] = strategy.get("config_json", {})
        pair = strategy.get("pair")
        price = await price_feed.get_price(pair)
        if price is None:
            continue
        entry_price = float(config.get("entry_price", price))
        tp_pct = float(config.get("take_profit_pct", 0))
        sl_pct = float(config.get("stop_loss_pct", 0))
        take_profit_price = entry_price * (1 + tp_pct / 100)
        stop_loss_price = entry_price * (1 - sl_pct / 100)
        should_take_profit = tp_pct and price >= take_profit_price
        should_stop_loss = sl_pct and price <= stop_loss_price
        if not (should_take_profit or should_stop_loss):
            continue
        side = "sell"
        amount = float(config.get("amount", 0.0) or 0)
        if amount <= 0:
            logger.warning("Strategi TP/SL tidak memiliki jumlah valid", extra={"strategy_id": strategy["id"]})
            continue
        try:
            await core_api_client.post(
                "/api/orders",
                {
                    "telegram_id": strategy["telegram_id"],
                    "pair": pair,
                    "side": side,
                    "type": "market",
                    "amount": amount,
                    "is_strategy_order": True,
                    "strategy_id": strategy["id"],
                },
                internal=True,
            )
            await core_api_client.post(
                f"/api/strategies/{strategy['id']}/executions",
                {
                    "user_id": strategy["user_id"],
                    "status": "success",
                    "detail": {
                        "price": price,
                        "action": "take_profit" if should_take_profit else "stop_loss",
                        "timestamp": now.to_iso8601_string(),
                    },
                },
                internal=True,
            )
            await send_notification(
                strategy["telegram_id"],
                (
                    "TP/SL terpicu\n"
                    f"Pair: {pair}\nHarga: {price:,.0f}\nAksi: {'Take Profit' if should_take_profit else 'Stop Loss'}"
                ),
                event_type="strategy_tp_sl_execution",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gagal eksekusi TP/SL", extra={"strategy_id": strategy.get("id")})
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
                f"Eksekusi TP/SL gagal: {exc}",
                event_type="strategy_tp_sl_failed",
            )
            if isinstance(exc, (httpx.HTTPError, asyncio.TimeoutError)):
                await trigger_deadman("Kesalahan komunikasi dengan Indodax", "tp_sl")
