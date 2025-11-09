from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from datetime import datetime
from html import escape
import httpx

from bot.services.api_client import core_api_client
from bot.services.token_store import token_store
from bot.utils.auth import parse_iso_datetime
from bot.utils.messages import (
    LINK_INSTRUCTION_TEXT,
    LINK_SECRET_PROMPT,
    LINK_SUCCESS_TEXT,
    TOKEN_EXPIRED_TEXT,
    TOKEN_MISSING_TEXT,
)

router = Router()


class LinkStates(StatesGroup):
    waiting_api_key = State()
    waiting_api_secret = State()


@router.message(Command("link"))
async def cmd_link(message: Message, state: FSMContext) -> None:
    await state.set_state(LinkStates.waiting_api_key)
    await message.answer(LINK_INSTRUCTION_TEXT)


@router.message(LinkStates.waiting_api_key)
async def process_api_key(message: Message, state: FSMContext) -> None:
    api_key = message.text.strip()
    if not api_key:
        await message.answer("API Key tidak boleh kosong. Mohon kirim ulang API Key Anda.")
        return
    await state.update_data(api_key=api_key)
    await state.set_state(LinkStates.waiting_api_secret)
    await message.answer(LINK_SECRET_PROMPT)


@router.message(LinkStates.waiting_api_secret)
async def process_api_secret(message: Message, state: FSMContext) -> None:
    api_secret = message.text.strip()
    if not api_secret:
        await message.answer("API Secret tidak boleh kosong. Mohon kirim ulang API Secret Anda.")
        return
    data = await state.get_data()
    api_key = data.get("api_key")
    if not api_key:
        await state.clear()
        await message.answer("Sesi tautan tidak valid. Silakan mulai ulang dengan /link.")
        return
    payload = {
        "telegram_id": message.from_user.id,
        "api_key": api_key,
        "api_secret": api_secret,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
    }
    try:
        response = await core_api_client.post("/api/auth/link-indodax", payload)
    except Exception as exc:  # noqa: BLE001
        await message.answer(
            f"Gagal menghubungkan API key: {escape(str(exc))}"
        )
        return
    if response.get("success"):
        token = response.get("data", {}).get("access_token")
        expires_at_raw = response.get("data", {}).get("token_expires_at")
        expires_at: datetime | None = parse_iso_datetime(expires_at_raw)
        if token:
            await token_store.set_token(
                message.from_user.id,
                token,
                expires_at=expires_at,
            )
        await message.answer(LINK_SUCCESS_TEXT)
    else:
        error_detail = response.get("error")
        await message.answer(
            f"Gagal: {escape(error_detail if isinstance(error_detail, str) else str(error_detail))}"
        )
    await state.clear()


@router.message(Command("unlink"))
async def cmd_unlink(message: Message) -> None:
    token, _ = await token_store.get_token_with_ttl(message.from_user.id)
    if not token:
        await message.answer(TOKEN_MISSING_TEXT)
        return
    try:
        response = await core_api_client.post(
            "/api/auth/revoke",
            {"telegram_id": message.from_user.id},
            user_token=token,
        )
        if response.get("success"):
            await token_store.delete_token(message.from_user.id)
            await message.answer(
                "Token akses berhasil dicabut. Hubungkan kembali dengan /link jika diperlukan."
            )
            return
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            await token_store.delete_token(message.from_user.id)
            await message.answer(TOKEN_EXPIRED_TEXT)
            return
        await message.answer("Gagal mencabut token akses. Mohon coba lagi nanti.")
        return
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Terjadi kesalahan: {exc}")
        return
    await message.answer("Gagal mencabut token akses. Mohon coba lagi nanti.")
