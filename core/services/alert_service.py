from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.models import PriceAlerts
from core.repositories.user_repository import user_repository


class AlertService:
    async def create_alert(
        self,
        session: AsyncSession,
        telegram_id: int,
        pair: str,
        target_price: float,
        direction: str,
        repeat: bool = False,
    ) -> PriceAlerts:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")

        alert = PriceAlerts(
            user_id=user.id,
            pair=pair,
            target_price=target_price,
            direction=direction,
            repeat=repeat,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return alert

    async def list_active_alerts(self, session: AsyncSession) -> list[PriceAlerts]:
        from core.models import Users

        result = await session.execute(
            select(PriceAlerts, Users.telegram_id)
            .join(Users, PriceAlerts.user_id == Users.id)
            .where(PriceAlerts.is_triggered.is_(False))
        )
        enriched: list[dict] = []
        for alert, telegram_id in result.all():
            payload = alert.model_dump()
            payload["telegram_id"] = telegram_id
            enriched.append(payload)
        return enriched

    async def list_alerts_for_user(
        self, session: AsyncSession, telegram_id: int
    ) -> list[dict]:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            return []
        result = await session.execute(
            select(PriceAlerts).where(PriceAlerts.user_id == user.id)
        )
        return [alert.model_dump() for alert in result.scalars().all()]

    async def mark_triggered(
        self, session: AsyncSession, alert_id: int
    ) -> PriceAlerts | None:
        result = await session.execute(
            select(PriceAlerts).where(PriceAlerts.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            return None
        alert.triggered_at = datetime.utcnow()
        if alert.repeat:
            await session.commit()
            await session.refresh(alert)
            return alert
        alert.is_triggered = True
        await session.commit()
        await session.refresh(alert)
        return alert


alert_service = AlertService()
