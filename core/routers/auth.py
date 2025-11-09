from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.repositories.key_repository import user_key_repository
from core.repositories.user_repository import user_repository
from core.schemas.auth import (
    AuthStatusResponse,
    LinkIndodaxRequest,
    TokenActionRequest,
    TokenRefreshResponse,
)
from core.schemas.common import APIResponse
from core.services.auth_service import auth_service
from core.routers.dependencies import require_internal_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/link-indodax", response_model=APIResponse[AuthStatusResponse])
async def link_indodax(
    payload: LinkIndodaxRequest,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[AuthStatusResponse]:
    try:
        _, token, expires_at = await auth_service.link_indodax_keys(
            session,
            telegram_id=payload.telegram_id,
            api_key=payload.api_key,
            api_secret=payload.api_secret,
            username=payload.username,
            full_name=payload.full_name,
        )
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        return APIResponse(success=False, data=None, error=str(exc))

    return APIResponse(
        success=True,
        data=AuthStatusResponse(
            is_connected=True,
            access_token=token,
            token_expires_at=expires_at,
        ),
    )


@router.get("/status", response_model=APIResponse[AuthStatusResponse])
async def auth_status(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[AuthStatusResponse]:
    user = await user_repository.get_by_telegram_id(session, telegram_id)
    if not user:
        return APIResponse(success=True, data=AuthStatusResponse(is_connected=False))
    key = await user_key_repository.get_active_key(session, user.id)
    token_expires_at = getattr(user, "api_token_expires_at", None)
    should_refresh = False
    if user.api_token_hash and token_expires_at:
        should_refresh = auth_service.should_rotate_token(user)
    return APIResponse(
        success=True,
        data=AuthStatusResponse(
            is_connected=key is not None,
            token_expires_at=token_expires_at,
            should_refresh=should_refresh,
        ),
    )


@router.post("/refresh-token", response_model=APIResponse[TokenRefreshResponse])
async def refresh_token(
    payload: TokenActionRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[TokenRefreshResponse]:
    try:
        token, expires_at = await auth_service.refresh_user_token(
            session, payload.telegram_id, authorization
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return APIResponse(
        success=True,
        data=TokenRefreshResponse(access_token=token, token_expires_at=expires_at),
    )


@router.post("/revoke", response_model=APIResponse[None])
async def revoke_token(
    payload: TokenActionRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[None]:
    try:
        await auth_service.revoke_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return APIResponse(success=True, data=None)


@router.post("/admin/revoke", response_model=APIResponse[None])
async def admin_revoke_token(
    payload: TokenActionRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[None]:
    try:
        await auth_service.admin_revoke_user_token(session, payload.telegram_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIResponse(success=True, data=None)
