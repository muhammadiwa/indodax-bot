from datetime import datetime

from pydantic import BaseModel, Field


class LinkIndodaxRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user id")
    api_key: str
    api_secret: str
    username: str | None = None
    full_name: str | None = None


class AuthStatusResponse(BaseModel):
    is_connected: bool
    access_token: str | None = None
    token_expires_at: datetime | None = None
    should_refresh: bool = False


class TokenActionRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user id")


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_expires_at: datetime
