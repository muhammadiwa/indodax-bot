from __future__ import annotations

import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    strategy_interval_keyboard,
    strategy_menu_keyboard,
    strategy_pairs_keyboard,
)
from bot.services.api_client import core_api_client
from bot.utils.auth import get_user_token
from bot.utils.market import get_top_pairs
from bot.utils.messages import STRATEGY_LIST_EMPTY

router = Router()


class StrategyStates(StatesGroup):
    choosing_action = State()
    dca_amount = State()
    dca_time = State()
    dca_max = State()
    grid_lower = State()
    grid_upper = State()
    grid_count = State()
    grid_size = State()
    tp_entry = State()
    tp_take = State()
    tp_stop = State()
    tp_amount = State()


async def _show_strategy_menu(message: Message, *, edit: bool = False) -> None:
    text = "Kelola strategi otomatis Anda:"
    markup = strategy_menu_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("strategy"))
async def cmd_strategy(message: Message, state: FSMContext) -> None:
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _show_strategy_menu(message)
    await state.set_state(StrategyStates.choosing_action)


@router.callback_query(F.data == "menu_strategy")
async def menu_strategy(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _show_strategy_menu(callback.message, edit=True)
    await state.set_state(StrategyStates.choosing_action)
    await callback.answer()


@router.callback_query(F.data == "strategy:menu")
async def strategy_back(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _show_strategy_menu(callback.message, edit=True)
    await state.set_state(StrategyStates.choosing_action)
    await callback.answer()


@router.callback_query(F.data.startswith("strategy:create:"))
async def strategy_create(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    mode = callback.data.split(":")[2]
    pairs = await get_top_pairs()
    await callback.message.edit_text(
        "Pilih pair untuk strategi:",
        reply_markup=strategy_pairs_keyboard(pairs, mode),
    )
    await state.set_state(StrategyStates.choosing_action)
    await state.update_data(mode=mode)
    await callback.answer()


@router.callback_query(F.data.startswith("strategy:pair:"))
async def strategy_pair(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    _, _, mode, pair = callback.data.split(":")
    await state.update_data(pair=pair)
    if mode == "dca":
        await callback.message.edit_text(
            f"Masukkan nominal IDR per eksekusi untuk {pair}:"
        )
        await state.set_state(StrategyStates.dca_amount)
    elif mode == "grid":
        await callback.message.edit_text(
            f"Masukkan harga bawah grid untuk {pair} (IDR):"
        )
        await state.set_state(StrategyStates.grid_lower)
    else:
        await callback.message.edit_text(
            f"Masukkan harga entry untuk {pair} (IDR):"
        )
        await state.set_state(StrategyStates.tp_entry)
    await state.update_data(mode=mode)
    await callback.answer()


def _parse_float(text: str) -> float | None:
    try:
        return float(text.replace(",", "").strip())
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


@router.message(StrategyStates.dca_amount)
async def dca_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_float(message.text)
    if not amount or amount <= 0:
        await message.reply("Nominal tidak valid.")
        return
    await state.update_data(amount=amount)
    await message.answer("Pilih interval strategi:", reply_markup=strategy_interval_keyboard())


@router.callback_query(F.data.startswith("strategy:dca:interval:"))
async def dca_interval(callback: CallbackQuery, state: FSMContext) -> None:
    interval = callback.data.split(":")[3]
    await state.update_data(interval=interval)
    await state.set_state(StrategyStates.dca_time)
    await callback.message.edit_text("Masukkan jam eksekusi (format HH:MM, WIB):")
    await callback.answer()


@router.message(StrategyStates.dca_time)
async def dca_time(message: Message, state: FSMContext) -> None:
    if not re.fullmatch(r"\d{2}:\d{2}", message.text.strip()):
        await message.reply("Format jam tidak valid.")
        return
    await state.update_data(execution_time=message.text.strip())
    await state.set_state(StrategyStates.dca_max)
    await message.answer(
        "Masukkan jumlah eksekusi maksimal (angka) atau ketik skip untuk tanpa batas:"
    )


@router.message(StrategyStates.dca_max)
async def dca_max(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    max_runs = None
    if text not in {"skip", "tanpa batas", ""}:
        value = _parse_int(text)
        if value is None or value < 1:
            await message.reply("Masukkan angka positif atau ketik skip.")
            return
        max_runs = value
    data = await state.get_data()
    payload = {
        "telegram_id": message.from_user.id,
        "name": "DCA",
        "pair": data.get("pair"),
        "amount": float(data.get("amount")),
        "interval": data.get("interval"),
        "execution_time": data.get("execution_time"),
        "max_runs": max_runs,
    }
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    try:
        await core_api_client.post("/api/strategies/dca", payload, user_token=token)
    except Exception as exc:  # noqa: BLE001
        await message.reply(f"Gagal menyimpan strategi: {exc}")
        await state.clear()
        return
    await message.answer("Strategi DCA berhasil disimpan.")
    await state.clear()


@router.message(StrategyStates.grid_lower)
async def grid_lower(message: Message, state: FSMContext) -> None:
    lower = _parse_float(message.text)
    if not lower or lower <= 0:
        await message.reply("Harga tidak valid.")
        return
    await state.update_data(lower_price=lower)
    await state.set_state(StrategyStates.grid_upper)
    await message.answer("Masukkan harga atas grid (IDR):")


@router.message(StrategyStates.grid_upper)
async def grid_upper(message: Message, state: FSMContext) -> None:
    upper = _parse_float(message.text)
    if not upper or upper <= 0:
        await message.reply("Harga tidak valid.")
        return
    data = await state.get_data()
    if upper <= data.get("lower_price", 0):
        await message.reply("Harga atas harus lebih tinggi dari harga bawah.")
        return
    await state.update_data(upper_price=upper)
    await state.set_state(StrategyStates.grid_count)
    await message.answer("Masukkan jumlah grid (contoh 6):")


@router.message(StrategyStates.grid_count)
async def grid_count(message: Message, state: FSMContext) -> None:
    count = _parse_int(message.text)
    if not count or count < 2:
        await message.reply("Jumlah grid minimal 2.")
        return
    await state.update_data(grid_count=count)
    await state.set_state(StrategyStates.grid_size)
    await message.answer("Masukkan ukuran order per grid (jumlah coin):")


@router.message(StrategyStates.grid_size)
async def grid_size(message: Message, state: FSMContext) -> None:
    size = _parse_float(message.text)
    if not size or size <= 0:
        await message.reply("Jumlah coin tidak valid.")
        return
    data = await state.get_data()
    payload = {
        "telegram_id": message.from_user.id,
        "name": "Grid",  # noqa: RUF100
        "pair": data.get("pair"),
        "lower_price": data.get("lower_price"),
        "upper_price": data.get("upper_price"),
        "grid_count": data.get("grid_count"),
        "order_size": size,
    }
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    try:
        await core_api_client.post("/api/strategies/grid", payload, user_token=token)
    except Exception as exc:  # noqa: BLE001
        await message.reply(f"Gagal menyimpan strategi: {exc}")
        await state.clear()
        return
    await message.answer("Strategi grid berhasil disimpan.")
    await state.clear()


@router.message(StrategyStates.tp_entry)
async def tp_entry(message: Message, state: FSMContext) -> None:
    entry = _parse_float(message.text)
    if not entry or entry <= 0:
        await message.reply("Harga entry tidak valid.")
        return
    await state.update_data(entry_price=entry)
    await state.set_state(StrategyStates.tp_take)
    await message.answer("Masukkan persentase take-profit (%):")


@router.message(StrategyStates.tp_take)
async def tp_take(message: Message, state: FSMContext) -> None:
    take = _parse_float(message.text)
    if not take or take <= 0:
        await message.reply("Persentase tidak valid.")
        return
    await state.update_data(take_profit_pct=take)
    await state.set_state(StrategyStates.tp_stop)
    await message.answer("Masukkan persentase stop-loss (%):")


@router.message(StrategyStates.tp_stop)
async def tp_stop(message: Message, state: FSMContext) -> None:
    stop = _parse_float(message.text)
    if not stop or stop <= 0:
        await message.reply("Persentase tidak valid.")
        return
    await state.update_data(stop_loss_pct=stop)
    await state.set_state(StrategyStates.tp_amount)
    await message.answer("Masukkan jumlah coin yang dipantau:")


@router.message(StrategyStates.tp_amount)
async def tp_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_float(message.text)
    if not amount or amount <= 0:
        await message.reply("Jumlah coin tidak valid.")
        return
    data = await state.get_data()
    payload = {
        "telegram_id": message.from_user.id,
        "name": "TP/SL",
        "pair": data.get("pair"),
        "entry_price": data.get("entry_price"),
        "take_profit_pct": data.get("take_profit_pct"),
        "stop_loss_pct": data.get("stop_loss_pct"),
        "amount": amount,
    }
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    try:
        await core_api_client.post("/api/strategies/tp-sl", payload, user_token=token)
    except Exception as exc:  # noqa: BLE001
        await message.reply(f"Gagal menyimpan strategi: {exc}")
        await state.clear()
        return
    await message.answer("Strategi TP/SL berhasil disimpan.")
    await state.clear()


@router.callback_query(F.data == "strategy:list")
async def strategy_list(callback: CallbackQuery) -> None:
    summary_lines: list[str] = []
    user_id = callback.from_user.id
    token = await get_user_token(callback)
    if not token:
        return
    response = await core_api_client.get(
        "/api/strategies/mine",
        {"telegram_id": user_id},
        user_token=token,
    )
    strategies = response.get("data", [])
    grouped: dict[str, list[dict]] = {"dca": [], "grid": [], "tp_sl": []}
    for item in strategies:
        grouped.setdefault(item.get("type", ""), []).append(item)
    for strategy_type, label in [
        ("dca", "DCA"),
        ("grid", "Grid"),
        ("tp_sl", "TP/SL"),
    ]:
        items = grouped.get(strategy_type) or []
        if not items:
            continue
        summary_lines.append(f"{label}:")
        for item in items:
            detail = item.get("config_json", {})
            summary_lines.append(f"- {item.get('name')} {item.get('pair')}: {detail}")
    text = "\n".join(summary_lines) if summary_lines else STRATEGY_LIST_EMPTY
    await callback.message.edit_text(text, reply_markup=strategy_menu_keyboard())
    await callback.answer()
