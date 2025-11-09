from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    str(_settings.database_url),
    echo=False,
    future=True,
)

async_session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
