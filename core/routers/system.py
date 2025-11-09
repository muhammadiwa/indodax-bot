from fastapi import APIRouter, Depends
from core.routers.dependencies import require_internal_token
from core.schemas.common import APIResponse
from core.services.safety_service import safety_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=APIResponse[dict])
async def get_status() -> APIResponse[dict]:
    status = await safety_service.get_status()
    return APIResponse(success=True, data=status)


@router.post("/pause", response_model=APIResponse[dict])
async def pause_system(
    payload: dict[str, str] | None,
    _: None = Depends(require_internal_token),
) -> APIResponse[dict]:
    payload = payload or {}
    reason = payload.get("reason") or "Pause oleh sistem"
    source = payload.get("source")
    status = await safety_service.pause(reason=reason, source=source)
    return APIResponse(success=True, data=status)


@router.post("/resume", response_model=APIResponse[dict])
async def resume_system(
    _: None = Depends(require_internal_token),
) -> APIResponse[dict]:
    status = await safety_service.resume()
    return APIResponse(success=True, data=status)
