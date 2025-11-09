from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_keyboard, market_pairs_keyboard
from bot.services.api_client import core_api_client
from bot.utils.market import get_top_pairs

router = Router()


async def _render_market_pairs(message: Message, *, edit: bool = False) -> None:
    pairs = await get_top_pairs()
    text = "Pilih pair untuk melihat harga dan statistik 24 jam:"
    markup = market_pairs_keyboard(pairs)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("market"))
async def cmd_market(message: Message) -> None:
    await _render_market_pairs(message)


@router.callback_query(F.data == "menu_market")
async def menu_market(callback: CallbackQuery) -> None:
    await _render_market_pairs(callback.message, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("market:pair:"))
async def market_pair_detail(callback: CallbackQuery) -> None:
    pair = callback.data.split(":")[2]
    base = pair[:-3] if len(pair) > 3 else pair
    response = await core_api_client.get("/api/market/tickers")
    ticker = response.get("data", {}).get("tickers", {}).get(pair.lower())
    if not ticker:
        await callback.answer("Data tidak tersedia", show_alert=True)
        return
    def _float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    last = _float(ticker.get("last"))
    high = _float(ticker.get("high"))
    low = _float(ticker.get("low"))
    percent = _float(ticker.get("percent_change"))
    volume = (
        _float(ticker.get(f"vol_{base.lower()}"))
        or _float(ticker.get("volume"))
        or _float(ticker.get("vol"))
    )
    direction = "📈" if percent >= 0 else "📉"
    text = (
        f"{pair.upper()}\n"
        f"Harga terakhir: {last:,.0f} IDR\n"
        f"Perubahan 24h: {direction} {percent:.2f}%\n"
        f"Tertinggi 24h: {high:,.0f} IDR\n"
        f"Terendah 24h: {low:,.0f} IDR\n"
        f"Volume {base.upper()}: {volume:,.4f}"
    )
    pairs = await get_top_pairs()
    await callback.message.edit_text(text, reply_markup=market_pairs_keyboard(pairs))
    await callback.answer()
