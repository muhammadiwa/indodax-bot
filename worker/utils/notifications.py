from __future__ import annotations

from typing import Any

from worker.clients.core_api import core_api_client


async def send_notification(chat_id: int, text: str, *, event_type: str, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "type": event_type,
    }
    if extra:
        payload["meta"] = extra
    await core_api_client.post("/api/notifications", payload, internal=True)
