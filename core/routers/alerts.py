from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.schemas.alert import AlertRequest
from core.schemas.common import APIResponse
from core.services.alert_service import alert_service
from core.services.auth_service import auth_service
from core.routers.dependencies import require_internal_token

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("")
async def create_alert(
    payload: AlertRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        alert = await alert_service.create_alert(
            session,
            telegram_id=payload.telegram_id,
            pair=payload.pair,
            target_price=payload.target_price,
            direction=payload.direction,
            repeat=payload.repeat,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=alert.model_dump())


@router.get("/active")
async def list_active_alerts(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[list[dict]]:
    alerts = await alert_service.list_active_alerts(session)
    return APIResponse(success=True, data=alerts)


@router.post("/{alert_id}/trigger")
async def trigger_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[dict | None]:
    alert = await alert_service.mark_triggered(session, alert_id)
    return APIResponse(success=True, data=alert.model_dump() if alert else None)


@router.get("/mine")
async def list_my_alerts(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[list[dict]]:
    try:
        await auth_service.verify_user_token(session, telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    alerts = await alert_service.list_alerts_for_user(session, telegram_id)
    return APIResponse(success=True, data=alerts)
