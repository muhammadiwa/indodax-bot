from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_keyboard
from bot.services.api_client import core_api_client
from bot.utils.auth import get_user_token
from bot.utils.messages import PORTFOLIO_ROW_TEMPLATE

router = Router()


async def _render_portfolio(
    message: Message,
    telegram_id: int,
    user_token: str,
    *,
    edit: bool = False,
) -> None:
    response = await core_api_client.get(
        "/api/portfolio",
        params={"telegram_id": telegram_id},
        user_token=user_token,
    )
    data = response.get("data", {})
    balances = data.get("balances", [])
    if not balances:
        text = "Tidak ada saldo aktif yang terdeteksi."
    else:
        rows = [
            PORTFOLIO_ROW_TEMPLATE.format(
                asset=item.get("asset"),
                amount=float(item.get("amount", 0.0)),
                value=float(item.get("value_idr", 0.0)),
                pct=float(item.get("allocation_pct", 0.0)),
            )
            for item in balances
        ]
        total = float(data.get("total_value_idr", 0.0))
        text = "Portofolio saat ini:\n" + "\n".join(rows)
        text += f"\n\nTotal estimasi: {total:,.0f} IDR"
    if edit:
        await message.edit_text(text, reply_markup=main_menu_keyboard())
    else:
        await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message) -> None:
    token = await get_user_token(message)
    if not token:
        return
    await _render_portfolio(message, message.from_user.id, token)


@router.callback_query(F.data == "menu_portfolio")
async def menu_portfolio(callback: CallbackQuery) -> None:
    token = await get_user_token(callback)
    if not token:
        return
    await _render_portfolio(callback.message, callback.from_user.id, token, edit=True)
    await callback.answer()
