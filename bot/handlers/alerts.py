from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    alert_pairs_keyboard,
    alerts_direction_keyboard,
    alerts_repeat_keyboard,
    main_menu_keyboard,
)
from bot.services.api_client import core_api_client
from bot.utils.auth import get_user_token
from bot.utils.market import get_top_pairs
from bot.utils.messages import ALERT_CREATED_TEXT

router = Router()


class AlertStates(StatesGroup):
    choosing_pair = State()
    waiting_price = State()
    choosing_direction = State()
    choosing_repeat = State()


async def _render_pairs(message: Message, *, edit: bool = False) -> None:
    pairs = await get_top_pairs()
    text = "Pilih pair untuk membuat price alert:"
    markup = alert_pairs_keyboard(pairs)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("alert"))
async def cmd_alert(message: Message, state: FSMContext) -> None:
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _render_pairs(message)
    await state.set_state(AlertStates.choosing_pair)


@router.callback_query(F.data == "menu_alerts")
async def menu_alerts(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _render_pairs(callback.message, edit=True)
    await state.set_state(AlertStates.choosing_pair)
    await callback.answer()


@router.callback_query(F.data.startswith("alert:pair:"))
async def alert_pair(callback: CallbackQuery, state: FSMContext) -> None:
    pair = callback.data.split(":")[2]
    await state.update_data(pair=pair)
    await state.set_state(AlertStates.waiting_price)
    await callback.message.edit_text(
        f"Masukkan harga target untuk {pair} (IDR):"
    )
    await callback.answer()


@router.message(AlertStates.waiting_price)
async def alert_price_input(message: Message, state: FSMContext) -> None:
    text = message.text.replace(",", "").strip()
    try:
        price = float(text)
    except ValueError:
        await message.reply("Harga tidak valid. Contoh: 500000000")
        return
    if price <= 0:
        await message.reply("Harga harus lebih besar dari nol.")
        return
    data = await state.get_data()
    pair = data.get("pair")
    await state.update_data(target_price=price)
    await state.set_state(AlertStates.choosing_direction)
    await message.answer(
        f"Pilih arah alert untuk {pair} pada {price:,.0f} IDR:",
        reply_markup=alerts_direction_keyboard(pair, price),
    )


@router.callback_query(F.data.startswith("alert:direction:"))
async def alert_direction(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, pair, target_str, direction = callback.data.split(":")
    await state.update_data(direction=direction)
    await state.set_state(AlertStates.choosing_repeat)
    await callback.message.edit_text(
        "Ingin alert dikirim sekali saja atau berulang?",
        reply_markup=alerts_repeat_keyboard(pair, float(target_str), direction),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("alert:repeat:"))
async def alert_repeat(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, pair, target_str, direction, repeat_flag = callback.data.split(":")
    data = await state.get_data()
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    payload = {
        "telegram_id": callback.from_user.id,
        "pair": pair,
        "target_price": float(data.get("target_price", target_str)),
        "direction": direction,
        "repeat": repeat_flag == "1",
    }
    try:
        response = await core_api_client.post("/api/alerts", payload, user_token=token)
    except Exception as exc:  # noqa: BLE001
        await callback.answer(f"Gagal: {exc}", show_alert=True)
        await state.clear()
        return
    if not response.get("success"):
        await callback.answer(
            response.get("error", "Gagal menyimpan alert"), show_alert=True
        )
        await state.clear()
        return
    await callback.message.edit_text(ALERT_CREATED_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()
    await state.clear()
