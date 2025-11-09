from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.models import Strategies, StrategyExecutions
from core.repositories.user_repository import user_repository


class StrategyService:
    async def create_or_update_dca(
        self,
        session: AsyncSession,
        telegram_id: int,
        *,
        name: str,
        pair: str,
        amount: float,
        interval: str,
        execution_time: str,
        max_runs: int | None,
    ) -> Strategies:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")

        config = {
            "type": "dca",
            "amount": amount,
            "interval": interval,
            "execution_time": execution_time,
            "max_runs": max_runs,
            "pair": pair,
        }

        result = await session.execute(
            select(Strategies).where(
                Strategies.user_id == user.id,
                Strategies.type == "dca",
                Strategies.pair == pair,
                Strategies.name == name,
            )
        )
        strategy = result.scalar_one_or_none()
        if strategy:
            strategy.config_json = config
            strategy.is_active = True
        else:
            strategy = Strategies(
                user_id=user.id,
                type="dca",
                name=name,
                pair=pair,
                config_json=config,
                is_active=True,
            )
            session.add(strategy)

        await session.commit()
        await session.refresh(strategy)
        return strategy

    async def create_grid(
        self,
        session: AsyncSession,
        telegram_id: int,
        *,
        name: str,
        pair: str,
        lower_price: float,
        upper_price: float,
        grid_count: int,
        order_size: float,
    ) -> Strategies:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")

        config = {
            "type": "grid",
            "lower_price": lower_price,
            "upper_price": upper_price,
            "grid_count": grid_count,
            "order_size": order_size,
        }
        strategy = Strategies(
            user_id=user.id,
            type="grid",
            name=name,
            pair=pair,
            config_json=config,
            is_active=True,
        )
        session.add(strategy)
        await session.commit()
        await session.refresh(strategy)
        return strategy

    async def create_tp_sl(
        self,
        session: AsyncSession,
        telegram_id: int,
        *,
        name: str,
        pair: str,
        entry_price: float,
        take_profit_pct: float,
        stop_loss_pct: float,
        amount: float,
    ) -> Strategies:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")

        config = {
            "type": "tp_sl",
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "amount": amount,
            "entry_price": entry_price,
        }
        strategy = Strategies(
            user_id=user.id,
            type="tp_sl",
            name=name,
            pair=pair,
            config_json=config,
            is_active=True,
        )
        session.add(strategy)
        await session.commit()
        await session.refresh(strategy)
        return strategy

    async def stop_strategy(self, session: AsyncSession, telegram_id: int, strategy_id: int) -> Strategies:
        result = await session.execute(
            select(Strategies).where(Strategies.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise ValueError("Strategi tidak ditemukan")
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user or strategy.user_id != user.id:
            raise ValueError("Tidak berhak menghentikan strategi")
        strategy.is_active = False
        await session.commit()
        await session.refresh(strategy)
        return strategy

    async def log_execution(
        self,
        session: AsyncSession,
        strategy_id: int,
        user_id: int,
        status: str,
        detail: dict[str, Any],
    ) -> StrategyExecutions:
        execution = StrategyExecutions(
            strategy_id=strategy_id,
            user_id=user_id,
            status=status,
            detail=detail,
            run_at=datetime.utcnow(),
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return execution

    async def list_active_by_type(
        self, session: AsyncSession, strategy_type: str
    ) -> list[dict[str, Any]]:
        from core.models import Users

        result = await session.execute(
            select(Strategies, Users.telegram_id)
            .join(Users, Strategies.user_id == Users.id)
            .where(Strategies.type == strategy_type, Strategies.is_active.is_(True))
        )
        data: list[dict[str, Any]] = []
        for strategy, telegram_id in result.all():
            entry = strategy.model_dump()
            entry["telegram_id"] = telegram_id
            data.append(entry)
        return data

    async def list_by_user(
        self, session: AsyncSession, telegram_id: int
    ) -> list[dict[str, Any]]:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            return []
        result = await session.execute(
            select(Strategies).where(Strategies.user_id == user.id)
        )
        return [strategy.model_dump() for strategy in result.scalars().all()]

    async def get_last_execution(
        self, session: AsyncSession, strategy_id: int
    ) -> StrategyExecutions | None:
        result = await session.execute(
            select(StrategyExecutions)
            .where(StrategyExecutions.strategy_id == strategy_id)
            .order_by(StrategyExecutions.created_at.desc())
        )
        return result.scalars().first()

    async def get_execution_count(self, session: AsyncSession, strategy_id: int) -> int:
        result = await session.execute(
            select(func.count(StrategyExecutions.id)).where(
                StrategyExecutions.strategy_id == strategy_id
            )
        )
        return result.scalar_one()


strategy_service = StrategyService()
