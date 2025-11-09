from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    orders_confirm_keyboard,
    orders_list_keyboard,
    trading_main_keyboard,
)
from bot.services.api_client import core_api_client
from bot.utils.auth import get_user_token

router = Router()


async def _render_orders(
    message: Message,
    telegram_id: int,
    user_token: str,
    *,
    edit: bool = False,
) -> None:
    response = await core_api_client.get(
        "/api/orders/open",
        params={"telegram_id": telegram_id},
        user_token=user_token,
    )
    orders = response.get("data", [])
    if not orders:
        text = "Tidak ada order aktif."
        markup = trading_main_keyboard()
        if edit:
            await message.edit_text(text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)
        return
    lines = []
    order_ids: list[int] = []
    for order in orders:
        order_ids.append(order["id"])
        price = order.get("price")
        price_display = f"{price:,.0f} IDR" if price else "Market"
        lines.append(
            f"#{order['id']} {order['pair']} {order['side'].upper()} "
            f"{order['amount']} @ {price_display}"
        )
    text = "Order aktif:\n" + "\n".join(lines)
    markup = orders_list_keyboard(order_ids, telegram_id)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("orders"))
async def cmd_orders(message: Message) -> None:
    token = await get_user_token(message)
    if not token:
        return
    await _render_orders(message, message.from_user.id, token)


@router.callback_query(F.data == "orders:list")
async def menu_orders(callback: CallbackQuery) -> None:
    token = await get_user_token(callback)
    if not token:
        return
    await _render_orders(callback.message, callback.from_user.id, token, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("orders:cancel:"))
async def cancel_request(callback: CallbackQuery) -> None:
    _, _, order_id_str, telegram_id_str = callback.data.split(":")
    if str(callback.from_user.id) != telegram_id_str:
        await callback.answer("Anda tidak dapat membatalkan order ini.", show_alert=True)
        return
    order_id = int(order_id_str)
    telegram_id = int(telegram_id_str)
    await callback.message.edit_reply_markup(
        reply_markup=orders_confirm_keyboard(order_id, telegram_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orders:confirm:"))
async def cancel_confirm(callback: CallbackQuery) -> None:
    _, _, order_id_str, telegram_id_str = callback.data.split(":")
    if str(callback.from_user.id) != telegram_id_str:
        await callback.answer("Anda tidak dapat membatalkan order ini.", show_alert=True)
        return
    token = await get_user_token(callback)
    if not token:
        return
    try:
        await core_api_client.post(
            f"/api/orders/{order_id_str}/cancel",
            params={"telegram_id": telegram_id_str},
            payload={},
            user_token=token,
        )
    except Exception as exc:  # noqa: BLE001
        await callback.answer(f"Gagal: {exc}", show_alert=True)
        return
    await _render_orders(callback.message, callback.from_user.id, token, edit=True)
    await callback.answer("Order dibatalkan")


@router.callback_query(F.data == "orders:cancelled")
async def cancel_decline(callback: CallbackQuery) -> None:
    token = await get_user_token(callback)
    if not token:
        return
    await _render_orders(callback.message, callback.from_user.id, token, edit=True)
    await callback.answer()
