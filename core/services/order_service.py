from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.encryption import decrypt_value
from core.indodax_private_client import private_client
from core.models import Orders, Users
from core.repositories.key_repository import user_key_repository
from core.repositories.user_repository import user_repository
from core.services.notification_service import notification_service
from core.services.safety_service import safety_service
from core.utils.rate_limiter import allow_action


class OrderService:
    async def create_order(
        self,
        session: AsyncSession,
        *,
        telegram_id: int,
        pair: str,
        side: str,
        order_type: str,
        amount: float,
        price: float | None = None,
        is_strategy_order: bool = False,
        strategy_id: int | None = None,
    ) -> Orders:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User belum terdaftar")

        safety_status = await safety_service.get_status()
        if safety_status["paused"]:
            reason = safety_status.get("reason") or "Trading sedang dijeda"
            raise ValueError(reason)

        key = await user_key_repository.get_active_key(session, user.id)
        if not key:
            raise ValueError("User belum menghubungkan API key")

        allowed = await allow_action(user.id, "order", limit=30, window_seconds=60)
        if not allowed:
            raise ValueError("Terlalu banyak order dalam waktu singkat")

        if is_strategy_order and not strategy_id:
            raise ValueError("strategy_id wajib untuk order strategi")
        if not is_strategy_order:
            strategy_id = None

        api_key = decrypt_value(key.api_key_nonce, key.api_key_ciphertext)
        api_secret = decrypt_value(key.api_secret_nonce, key.api_secret_ciphertext)

        params: dict[str, Any] = {
            "pair": pair.lower(),
            "type": side,
            "amount": amount,
        }
        if order_type == "limit" and price is not None:
            params["price"] = price
        elif order_type == "market":
            params["type"] = f"{side}_market"

        response = await private_client.call(
            user_id=user.id,
            method="trade",
            params=params,
            api_key=api_key,
            api_secret=api_secret,
        )

        order = Orders(
            user_id=user.id,
            indodax_order_id=str(response.get("return", {}).get("order_id")),
            pair=pair.upper(),
            side=side,
            type=order_type,
            price=price,
            amount=amount,
            status="open",
            is_strategy_order=is_strategy_order,
            strategy_id=strategy_id,
            raw_request=params,
            raw_response=response,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        notification_text = (
            "Order strategi" if is_strategy_order else "Order manual"
        )
        price_display = f"@ {price:,.0f} IDR" if price else "pasar"
        try:
            await notification_service.notify(
                {
                    "type": "order_submitted",
                    "chat_id": user.telegram_id,
                    "text": (
                        f"{notification_text} berhasil dikirim\\n"
                        f"Pair: {order.pair}\nArah: {order.side.upper()}\n"
                        f"Jumlah: {order.amount}\nHarga: {price_display}"
                    ),
                }
            )
        except Exception:  # noqa: BLE001
            pass
        return order

    async def get_open_orders(
        self,
        session: AsyncSession,
        telegram_id: int,
        *,
        pair: str | None = None,
        strategy_id: int | None = None,
    ) -> list[Orders]:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            return []
        query = select(Orders).where(Orders.user_id == user.id, Orders.status == "open")
        if pair:
            query = query.where(Orders.pair == pair.upper())
        if strategy_id is not None:
            query = query.where(Orders.strategy_id == strategy_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def cancel_order(
        self, session: AsyncSession, telegram_id: int, order_id: int
    ) -> Orders:
        from sqlmodel import select

        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")

        result = await session.execute(
            select(Orders).where(Orders.id == order_id, Orders.user_id == user.id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError("Order tidak ditemukan")

        key = await user_key_repository.get_active_key(session, user.id)
        if not key:
            raise ValueError("API key tidak tersedia")

        api_key = decrypt_value(key.api_key_nonce, key.api_key_ciphertext)
        api_secret = decrypt_value(key.api_secret_nonce, key.api_secret_ciphertext)

        await private_client.call(
            user_id=user.id,
            method="cancelOrder",
            params={"order_id": order.indodax_order_id, "pair": order.pair.lower()},
            api_key=api_key,
            api_secret=api_secret,
        )

        order.status = "canceled"
        await session.commit()
        await session.refresh(order)
        return order

    async def sync_open_orders(
        self,
        session: AsyncSession,
        *,
        telegram_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        query = (
            select(Orders, Users)
            .join(Users, Orders.user_id == Users.id)
            .where(Orders.status == "open")
        )
        if telegram_ids:
            query = query.where(Users.telegram_id.in_(telegram_ids))
        result = await session.execute(query)
        rows = result.all()
        notifications: list[tuple[int, str]] = []
        details: list[dict[str, str]] = []
        updated = 0

        for order, user in rows:
            key = await user_key_repository.get_active_key(session, user.id)
            if not key or not order.indodax_order_id:
                continue
            api_key = decrypt_value(key.api_key_nonce, key.api_key_ciphertext)
            api_secret = decrypt_value(key.api_secret_nonce, key.api_secret_ciphertext)
            try:
                response = await private_client.call(
                    user_id=user.id,
                    method="openOrders",
                    params={"pair": order.pair.lower()},
                    api_key=api_key,
                    api_secret=api_secret,
                )
            except Exception:  # noqa: BLE001
                continue

            open_orders = response.get("return", {}).get("orders", []) or []
            found = next(
                (
                    item
                    for item in open_orders
                    if str(item.get("order_id")) == order.indodax_order_id
                ),
                None,
            )
            if found:
                continue

            order.status = "filled"
            order.updated_at = datetime.utcnow()
            updated += 1
            details.append({
                "order_id": str(order.id),
                "status": "filled",
            })
            price_display = (
                f"@ {order.price:,.0f} IDR" if order.price else "pasar"
            )
            notifications.append(
                (
                    user.telegram_id,
                    (
                        "Order selesai terisi\\n"
                        f"Pair: {order.pair}\nArah: {order.side.upper()}\n"
                        f"Jumlah: {order.amount}\nHarga: {price_display}"
                    ),
                )
            )

        if updated:
            await session.commit()
            for chat_id, text in notifications:
                try:
                    await notification_service.notify(
                        {"type": "order_filled", "chat_id": chat_id, "text": text}
                    )
                except Exception:  # noqa: BLE001
                    continue
        return {"updated": updated, "details": details}


order_service = OrderService()
