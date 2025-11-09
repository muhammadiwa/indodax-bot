from fastapi import Depends, Header, HTTPException, status

from core.config import get_settings


async def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    settings=Depends(get_settings),
) -> None:
    if not settings.internal_auth_token:
        return
    if not x_internal_token or x_internal_token != settings.internal_auth_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token internal tidak valid",
        )


async def is_internal_request(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    settings=Depends(get_settings),
) -> bool:
    if not settings.internal_auth_token:
        return False
    return x_internal_token == settings.internal_auth_token
