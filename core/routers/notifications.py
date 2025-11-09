from fastapi import APIRouter, Depends, HTTPException

from core.routers.dependencies import require_internal_token
from core.schemas.common import APIResponse
from core.services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("", response_model=APIResponse[dict])
async def push_notification(
    payload: dict,
    _: None = Depends(require_internal_token),
) -> APIResponse[dict]:
    try:
        await notification_service.notify(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return APIResponse(success=True, data={"delivered": True})
