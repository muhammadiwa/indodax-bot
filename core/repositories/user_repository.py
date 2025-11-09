from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.models import Users


class UserRepository:
    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: int) -> Optional[Users]:
        result = await session.execute(select(Users).where(Users.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Users:
        user = await self.get_by_telegram_id(session, telegram_id)
        if user:
            user.username = username
            user.full_name = full_name
        else:
            user = Users(telegram_id=telegram_id, username=username, full_name=full_name)
            session.add(user)
        await session.flush()
        return user

    async def update_api_token(
        self,
        session: AsyncSession,
        user: Users,
        *,
        token_hash: str | None,
        expires_at: datetime | None,
    ) -> Users:
        user.api_token_hash = token_hash
        user.api_token_expires_at = expires_at
        session.add(user)
        await session.flush()
        return user


user_repository = UserRepository()
