from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.models import UserIndodaxKeys


class UserKeyRepository:
    async def get_active_key(self, session: AsyncSession, user_id: int) -> Optional[UserIndodaxKeys]:
        result = await session.execute(
            select(UserIndodaxKeys).where(
                UserIndodaxKeys.user_id == user_id,
                UserIndodaxKeys.is_active.is_(True),
            ).order_by(UserIndodaxKeys.created_at.desc())
        )
        return result.scalars().first()

    async def add_key(
        self,
        session: AsyncSession,
        user_id: int,
        api_key_nonce: bytes,
        api_key_ciphertext: bytes,
        api_secret_nonce: bytes,
        api_secret_ciphertext: bytes,
        label: Optional[str] = None,
    ) -> UserIndodaxKeys:
        await session.execute(
            UserIndodaxKeys.__table__.update()
            .where(UserIndodaxKeys.user_id == user_id)
            .values(is_active=False)
        )
        key = UserIndodaxKeys(
            user_id=user_id,
            api_key_nonce=api_key_nonce,
            api_key_ciphertext=api_key_ciphertext,
            api_secret_nonce=api_secret_nonce,
            api_secret_ciphertext=api_secret_ciphertext,
            label=label,
            is_active=True,
        )
        session.add(key)
        await session.flush()
        return key


user_key_repository = UserKeyRepository()
