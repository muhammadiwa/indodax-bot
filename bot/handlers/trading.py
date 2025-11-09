from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    confirmation_keyboard,
    trade_amount_keyboard,
    trade_pairs_keyboard,
    trade_price_keyboard,
    trade_side_keyboard,
    trade_type_keyboard,
    trading_main_keyboard,
)
from bot.services.api_client import core_api_client
from bot.utils.auth import get_user_token
from bot.utils.market import get_top_pairs
from bot.utils.messages import ORDER_SUMMARY_TEMPLATE

router = Router()


class TradeStates(StatesGroup):
    choosing_pair = State()
    choosing_side = State()
    choosing_type = State()
    waiting_price = State()
    waiting_amount = State()
    waiting_manual_amount = State()
    waiting_confirmation = State()


async def _render_pairs(message: Message, state: FSMContext, *, edit: bool = False) -> None:
    pairs = await get_top_pairs()
    text = "Pilih pair yang ingin ditradingkan:"
    markup = trade_pairs_keyboard(pairs)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)
    await state.set_state(TradeStates.choosing_pair)
    await state.update_data(pair=None, side=None, order_type=None, price=None, amount=None)


async def _get_price_payload(pair: str) -> dict:
    return await core_api_client.get(f"/api/market/price/{pair}")


async def _current_price(pair: str) -> float:
    payload = await _get_price_payload(pair)
    return float(payload.get("data", {}).get("price", 0.0))


def _base_asset(pair: str) -> str:
    return pair[:-3] if pair.upper().endswith("IDR") else pair.upper()


def _format_amount(amount: float, pair: str, idr_amount: float | None = None) -> str:
    base = _base_asset(pair)
    formatted = f"{amount:.8f} {base}"
    if idr_amount:
        formatted += f" (~{idr_amount:,.0f} IDR)"
    return formatted


@router.message(Command("price"))
async def cmd_price(message: Message) -> None:
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Gunakan format /price BTCIDR")
        return
    pair = parts[1].upper()
    try:
        payload = await _get_price_payload(pair)
        price = float(payload.get("data", {}).get("price", 0.0))
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Gagal mengambil harga: {exc}")
        return
    if not price:
        await message.answer("Pair tidak ditemukan atau tidak aktif.")
        return
    order_book = payload.get("data", {}).get("order_book", {})
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])

    def _format_side(levels: list[dict], label: str) -> str:
        if not levels:
            return f"{label}: -"
        lines = [label]
        for entry in levels:
            lines.append(
                f"• {entry.get('price', 0):,.0f} IDR | {entry.get('amount', 0):.6f}"
            )
        return "\n".join(lines)

    text = (
        f"Harga {pair} saat ini: {price:,.0f} IDR\n\n"
        f"Order Book Teratas:\n{_format_side(bids, 'Bid (Beli)')}\n\n"
        f"{_format_side(asks, 'Ask (Jual)')}"
    )
    await message.answer(text)


@router.message(Command("trade"))
async def cmd_trade(message: Message, state: FSMContext) -> None:
    token = await get_user_token(message)
    if not token:
        await state.clear()
        return
    await state.clear()
    await message.answer("Pilih aksi trading:", reply_markup=trading_main_keyboard())


@router.callback_query(F.data == "menu_trading")
async def menu_trading(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    await callback.message.edit_text("Pilih aksi trading:", reply_markup=trading_main_keyboard())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "trade:start")
async def trade_start(callback: CallbackQuery, state: FSMContext) -> None:
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    await state.clear()
    await _render_pairs(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data == "trade:back:pairs")
async def trade_back_pairs(callback: CallbackQuery, state: FSMContext) -> None:
    await _render_pairs(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("trade:pair:"))
async def trade_choose_pair(callback: CallbackQuery, state: FSMContext) -> None:
    pair = callback.data.split(":")[2].upper()
    await state.update_data(pair=pair, side=None, order_type=None, price=None, amount=None)
    await state.set_state(TradeStates.choosing_side)
    await callback.message.edit_text(
        f"Pair {pair} dipilih. Pilih aksi:", reply_markup=trade_side_keyboard(pair)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trade:side:"))
async def trade_choose_side(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, pair, side = callback.data.split(":")
    await state.update_data(pair=pair.upper(), side=side)
    await state.set_state(TradeStates.choosing_type)
    await callback.message.edit_text(
        f"Anda memilih {side.upper()} pada {pair.upper()}. Pilih tipe order:",
        reply_markup=trade_type_keyboard(pair.upper(), side),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trade:type:"))
async def trade_choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if parts[-1] == "back":
        data = await state.get_data()
        pair = data.get("pair") or "BTCIDR"
        await state.set_state(TradeStates.choosing_side)
        await callback.message.edit_text(
            f"Pair {pair} dipilih. Pilih aksi:", reply_markup=trade_side_keyboard(pair)
        )
        await callback.answer()
        return
    _, _, pair, side, order_type = parts
    await state.update_data(order_type=order_type, pair=pair.upper(), side=side)
    if order_type == "limit":
        await state.set_state(TradeStates.waiting_price)
        await callback.message.edit_text(
            "Masukkan harga limit (IDR) atau gunakan tombol di bawah.",
            reply_markup=trade_price_keyboard(pair.upper(), side),
        )
    else:
        await state.set_state(TradeStates.waiting_amount)
        await callback.message.edit_text(
            "Pilih nominal pembelian dalam IDR atau ketik jumlah coin.",
            reply_markup=trade_amount_keyboard(pair.upper(), side, order_type),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("trade:price:"))
async def trade_price_current(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, pair, side, action = callback.data.split(":")
    if action != "current":
        await callback.answer()
        return
    try:
        price = await _current_price(pair)
    except Exception as exc:  # noqa: BLE001
        await callback.answer(f"Gagal: {exc}", show_alert=True)
        return
    if not price:
        await callback.answer("Harga tidak tersedia", show_alert=True)
        return
    await state.update_data(price=price)
    await state.set_state(TradeStates.waiting_amount)
    await callback.message.edit_text(
        f"Harga limit ditetapkan {price:,.0f} IDR. Pilih nominal atau ketik jumlah coin.",
        reply_markup=trade_amount_keyboard(pair, side, "limit"),
    )
    await callback.answer()


@router.message(TradeStates.waiting_price)
async def trade_price_manual(message: Message, state: FSMContext) -> None:
    text = message.text.replace(",", "").strip()
    try:
        price = float(text)
    except ValueError:
        await message.reply("Harga tidak valid. Masukkan angka, contoh 450000000")
        return
    if price <= 0:
        await message.reply("Harga harus lebih besar dari nol.")
        return
    data = await state.get_data()
    pair = data.get("pair")
    side = data.get("side")
    await state.update_data(price=price)
    await state.set_state(TradeStates.waiting_amount)
    await message.answer(
        f"Harga limit diset {price:,.0f} IDR. Pilih nominal atau ketik jumlah coin.",
        reply_markup=trade_amount_keyboard(pair, side, "limit"),
    )


async def _resolve_execution_price(
    state: FSMContext, order_type: str, pair: str
) -> float:
    data = await state.get_data()
    if order_type == "limit":
        return float(data.get("price", 0.0))
    return await _current_price(pair)


async def _finalize_order(
    message: Message,
    state: FSMContext,
    *,
    amount_coin: float,
    idr_amount: float | None,
) -> None:
    data = await state.get_data()
    pair = data.get("pair")
    side = data.get("side")
    order_type = data.get("order_type")
    price = data.get("price") if order_type == "limit" else None
    amount_label = _format_amount(amount_coin, pair, idr_amount)
    summary = ORDER_SUMMARY_TEMPLATE.format(
        pair=pair,
        side=side.upper(),
        order_type=order_type.upper(),
        amount=amount_label,
        price=f"{price:,.0f} IDR" if price else "Market",
    )
    await state.update_data(amount=amount_coin, idr_amount=idr_amount)
    await state.set_state(TradeStates.waiting_confirmation)
    await message.answer(summary, reply_markup=confirmation_keyboard())


@router.callback_query(F.data.startswith("trade:amount:"))
async def trade_amount_quick(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    _, _, pair, side, order_type, mode, value = parts
    if mode == "coin" and value == "manual":
        await state.set_state(TradeStates.waiting_manual_amount)
        await callback.message.edit_text(
            "Ketik jumlah coin (contoh 0.01) atau tulis 'idr 500000' untuk nominal rupiah."
        )
        await callback.answer()
        return
    if mode != "idr":
        await callback.answer()
        return
    idr_value = float(value)
    price = await _resolve_execution_price(state, order_type, pair)
    if not price:
        await callback.answer("Harga tidak tersedia", show_alert=True)
        return
    amount_coin = idr_value / price
    await state.update_data(price=price if order_type == "limit" else None)
    await _finalize_order(callback.message, state, amount_coin=amount_coin, idr_amount=idr_value)
    await callback.answer()


@router.message(TradeStates.waiting_manual_amount)
@router.message(TradeStates.waiting_amount)
async def trade_amount_manual(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text in {"batal", "cancel"}:
        await state.clear()
        await message.reply("Order dibatalkan.")
        return
    data = await state.get_data()
    pair = data.get("pair")
    order_type = data.get("order_type")
    if text.startswith("idr"):
        amount_text = text.replace("idr", "").strip().replace(",", "")
        try:
            idr_value = float(amount_text)
        except ValueError:
            await message.reply("Nominal IDR tidak valid.")
            return
        price = await _resolve_execution_price(state, order_type, pair)
        if not price:
            await message.reply("Harga tidak tersedia. Coba lagi.")
            return
        amount_coin = idr_value / price
        await _finalize_order(message, state, amount_coin=amount_coin, idr_amount=idr_value)
        return
    try:
        amount_coin = float(text)
    except ValueError:
        await message.reply("Masukkan jumlah coin valid atau format 'idr <nominal>'.")
        return
    if amount_coin <= 0:
        await message.reply("Jumlah coin harus lebih besar dari nol.")
        return
    await _finalize_order(message, state, amount_coin=amount_coin, idr_amount=None)


@router.callback_query(F.data == "trade:cancel")
async def trade_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Order dibatalkan.")
    await callback.answer()


@router.callback_query(F.data == "trade:confirm")
async def trade_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pair = data.get("pair")
    side = data.get("side")
    order_type = data.get("order_type")
    amount = float(data.get("amount", 0))
    price = data.get("price") if order_type == "limit" else None
    payload = {
        "telegram_id": callback.from_user.id,
        "pair": pair,
        "side": side,
        "type": order_type,
        "amount": amount,
        "price": price,
    }
    token = await get_user_token(callback)
    if not token:
        await state.clear()
        return
    try:
        response = await core_api_client.post("/api/orders", payload, user_token=token)
    except Exception as exc:  # noqa: BLE001
        await callback.message.edit_text(f"Gagal mengirim order: {exc}")
        await callback.answer()
        await state.clear()
        return
    if response.get("success"):
        await callback.message.edit_text("Order berhasil dikirim ke Indodax.")
    else:
        error = response.get("error") or "Gagal mengirim order"
        await callback.message.edit_text(f"Gagal: {error}")
    await state.clear()
    await callback.answer()
