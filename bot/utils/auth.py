from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from aiogram.types import CallbackQuery, Message
import httpx
import logging

from bot.config import get_settings
from bot.services.api_client import core_api_client
from bot.services.token_store import token_store
from bot.utils.messages import TOKEN_EXPIRED_TEXT, TOKEN_MISSING_TEXT

UserInteraction = Union[Message, CallbackQuery]


async def get_user_token(event: UserInteraction) -> Optional[str]:
    telegram_id = event.from_user.id
    token, ttl = await token_store.get_token_with_ttl(telegram_id)
    if not token:
        await _notify_missing_token(event)
        return None

    settings = get_settings()
    if ttl is not None and ttl <= settings.user_token_refresh_threshold_seconds:
        token = await _attempt_token_refresh(event, telegram_id, token)
        if not token:
            return None
    return token


def parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


async def _attempt_token_refresh(
    event: UserInteraction, telegram_id: int, token: str
) -> Optional[str]:
    logger = logging.getLogger(__name__)
    try:
        response = await core_api_client.post(
            "/api/auth/refresh-token",
            {"telegram_id": telegram_id},
            user_token=token,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            await token_store.delete_token(telegram_id)
            await _notify_expired_token(event)
            return None
        logger.warning("Gagal me-refresh token pengguna", exc_info=exc)
        return token
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gagal me-refresh token pengguna", exc_info=exc)
        return token

    if not response.get("success"):
        logger.warning(
            "Core API menolak refresh token", extra={"telegram_id": telegram_id}
        )
        return token

    data = response.get("data", {})
    new_token = data.get("access_token")
    expires_at_str = data.get("token_expires_at")
    expires_at = parse_iso_datetime(expires_at_str)
    if new_token:
        await token_store.set_token(
            telegram_id,
            new_token,
            expires_at=expires_at,
        )
        return new_token
    return token


async def _notify_missing_token(event: UserInteraction) -> None:
    if isinstance(event, CallbackQuery):
        await event.message.answer(TOKEN_MISSING_TEXT)
        await event.answer("Hubungkan API key terlebih dahulu", show_alert=True)
    else:
        await event.answer(TOKEN_MISSING_TEXT)


async def _notify_expired_token(event: UserInteraction) -> None:
    if isinstance(event, CallbackQuery):
        await event.message.answer(TOKEN_EXPIRED_TEXT)
        await event.answer("Token kedaluwarsa", show_alert=True)
    else:
        await event.answer(TOKEN_EXPIRED_TEXT)
