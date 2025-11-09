import logging

import pendulum

from worker.clients.core_api import core_api_client
from worker.config import get_settings
from worker.price_feed import price_feed
from worker.utils.notifications import send_notification

logger = logging.getLogger(__name__)


async def check_price_alerts() -> None:
    settings = get_settings()
    now = pendulum.now(settings.scheduler_timezone)
    alerts_response = await core_api_client.get(
        "/api/alerts/active",
        internal=True,
    )
    alerts = alerts_response.get("data", [])
    for alert in alerts:
        pair = alert.get("pair")
        current_price = await price_feed.get_price(pair)
        if current_price is None:
            continue
        target = float(alert.get("target_price"))
        direction = alert.get("direction")
        triggered = False
        if direction == "up" and current_price >= target:
            triggered = True
        elif direction == "down" and current_price <= target:
            triggered = True
        if not triggered:
            continue
        if not alert.get("repeat"):
            await core_api_client.post(
                f"/api/alerts/{alert['id']}/trigger",
                {},
                internal=True,
            )
        logger.info(
            "Alert terpenuhi",
            extra={
                "alert_id": alert.get("id"),
                "pair": pair,
                "price": current_price,
                "time": now.to_iso8601_string(),
            },
        )
        await send_notification(
            alert["telegram_id"],
            (
                "Alert harga terpenuhi\n"
                f"Pair: {pair}\nHarga saat ini: {current_price:,.0f}\n"
                f"Arah: {'≥' if direction == 'up' else '≤'} {target:,.0f}"
            ),
            event_type="price_alert_triggered",
            extra={"alert_id": alert.get("id"), "repeat": bool(alert.get("repeat"))},
        )
