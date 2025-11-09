import types
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest

pytest.importorskip("sqlalchemy")
httpx = pytest.importorskip("httpx")

from core.app import app
from core.database import get_session
from core.services.auth_service import auth_service
from bot.utils.auth import parse_iso_datetime


class DummySession:
    def __init__(self) -> None:
        self.rollback_called = False

    async def rollback(self) -> None:  # pragma: no cover - simple flag set
        self.rollback_called = True


@pytest.mark.asyncio
async def test_verify_user_token_expired(monkeypatch):
    raw_token = "sample-token"
    hashed = auth_service._hash_token(raw_token)
    user = types.SimpleNamespace(
        id=1,
        telegram_id=777,
        api_token_hash=hashed,
        api_token_expires_at=datetime.utcnow() - timedelta(seconds=10),
    )

    async def fake_get(session, telegram_id):
        return user

    dummy_repo = types.SimpleNamespace(get_by_telegram_id=fake_get)
    monkeypatch.setattr("core.services.auth_service.user_repository", dummy_repo)

    with pytest.raises(ValueError):
        await auth_service.verify_user_token(DummySession(), user.telegram_id, raw_token)


def test_parse_iso_datetime_with_z():
    value = "2024-01-01T00:00:00Z"
    result = parse_iso_datetime(value)
    assert result is not None
    assert result.tzinfo is not None


@pytest.mark.asyncio
async def test_link_indodax_returns_error_payload(monkeypatch):
    session_instance = DummySession()

    @asynccontextmanager
    async def override_session():
        yield session_instance

    async def fake_link(*args, **kwargs):  # noqa: D401
        raise ValueError("API key invalid")

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        "core.routers.auth.auth_service.link_indodax_keys",
        fake_link,
    )

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/auth/link-indodax",
            json={
                "telegram_id": 1,
                "api_key": "test",
                "api_secret": "secret",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "API key invalid"
    assert session_instance.rollback_called is True

    app.dependency_overrides.pop(get_session, None)
