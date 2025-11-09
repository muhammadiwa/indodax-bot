from typing import Any, Generic, Type, TypeVar

from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get_by_id(self, session: AsyncSession, obj_id: Any) -> ModelType | None:
        result = await session.execute(select(self.model).where(self.model.id == obj_id))
        return result.scalar_one_or_none()

    async def add(self, session: AsyncSession, obj: ModelType) -> ModelType:
        session.add(obj)
        await session.flush()
        return obj

    async def list(self, session: AsyncSession, *filters: Any) -> list[ModelType]:
        statement = select(self.model)
        for f in filters:
            statement = statement.where(f)
        result = await session.execute(statement)
        return list(result.scalars().all())
