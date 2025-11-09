from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.schemas.common import APIResponse
from core.services.portfolio_service import portfolio_service
from core.services.auth_service import auth_service

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    data = await portfolio_service.get_portfolio(session, telegram_id)
    return APIResponse(success=True, data=data)
