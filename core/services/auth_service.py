from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import hashlib
import hmac
import logging
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.encryption import encrypt_value
from core.indodax_private_client import private_client
from core.models import Users
from core.repositories.key_repository import user_key_repository
from core.repositories.user_repository import user_repository


class AuthService:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    @property
    def settings(self):
        return get_settings()

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _extract_token(self, authorization_header: Optional[str]) -> str:
        if not authorization_header:
            raise ValueError("Token pengguna wajib disertakan")
        token = authorization_header
        if authorization_header.lower().startswith("bearer "):
            token = authorization_header.split(" ", 1)[1].strip()
        if not token:
            raise ValueError("Token pengguna wajib disertakan")
        return token

    async def _issue_new_token(
        self, session: AsyncSession, user: Users
    ) -> tuple[str, datetime]:
        raw_token = self._generate_token()
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(
            seconds=self.settings.user_token_ttl_seconds
        )
        await user_repository.update_api_token(
            session,
            user,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._logger.info(
            "auth.token_issued",
            extra={
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "expires_at": expires_at.isoformat(),
            },
        )
        return raw_token, expires_at

    def should_rotate_token(self, user: Users) -> bool:
        if not user.api_token_expires_at:
            return False
        remaining = (user.api_token_expires_at - datetime.utcnow()).total_seconds()
        return remaining <= self.settings.user_token_rotation_threshold_seconds

    async def link_indodax_keys(
        self,
        session: AsyncSession,
        telegram_id: int,
        api_key: str,
        api_secret: str,
        *,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> tuple[Users, str, datetime]:
        user = await user_repository.create_or_update(session, telegram_id, username, full_name)
        info = await private_client.call(
            user_id=user.id,
            method="getInfo",
            params={},
            api_key=api_key,
            api_secret=api_secret,
        )

        rights = info.get("return", {}).get("rights", {})
        if rights.get("withdraw"):
            raise ValueError("API key dengan hak withdraw tidak diperbolehkan")
        if not rights.get("trade"):
            raise ValueError("API key harus memiliki hak trade")

        nonce_key, api_key_cipher = encrypt_value(api_key)
        nonce_secret, api_secret_cipher = encrypt_value(api_secret)

        await user_key_repository.add_key(
            session,
            user_id=user.id,
            api_key_nonce=nonce_key,
            api_key_ciphertext=api_key_cipher,
            api_secret_nonce=nonce_secret,
            api_secret_ciphertext=api_secret_cipher,
        )

        raw_token, expires_at = await self._issue_new_token(session, user)
        await session.commit()
        return user, raw_token, expires_at

    async def verify_user_token(
        self,
        session: AsyncSession,
        telegram_id: int,
        authorization_header: Optional[str],
    ) -> Users:
        token = self._extract_token(authorization_header)
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user or not user.api_token_hash:
            raise ValueError("Token pengguna tidak valid")
        if not user.api_token_expires_at or user.api_token_expires_at <= datetime.utcnow():
            raise ValueError("Token pengguna sudah kedaluwarsa")
        provided_hash = self._hash_token(token)
        if not hmac.compare_digest(user.api_token_hash, provided_hash):
            raise ValueError("Token pengguna tidak valid")
        return user

    async def refresh_user_token(
        self,
        session: AsyncSession,
        telegram_id: int,
        authorization_header: Optional[str],
    ) -> tuple[str, datetime]:
        user = await self.verify_user_token(session, telegram_id, authorization_header)
        raw_token, expires_at = await self._issue_new_token(session, user)
        await session.commit()
        self._logger.info(
            "auth.token_rotated",
            extra={
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "expires_at": expires_at.isoformat(),
            },
        )
        return raw_token, expires_at

    async def revoke_user_token(
        self,
        session: AsyncSession,
        telegram_id: int,
        authorization_header: Optional[str],
    ) -> None:
        user = await self.verify_user_token(session, telegram_id, authorization_header)
        await user_repository.update_api_token(
            session,
            user,
            token_hash=None,
            expires_at=None,
        )
        await session.commit()
        self._logger.info(
            "auth.token_revoked",
            extra={"user_id": user.id, "telegram_id": user.telegram_id},
        )

    async def admin_revoke_user_token(
        self,
        session: AsyncSession,
        telegram_id: int,
    ) -> None:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError("User tidak ditemukan")
        await user_repository.update_api_token(
            session,
            user,
            token_hash=None,
            expires_at=None,
        )
        await session.commit()
        self._logger.info(
            "auth.token_revoked_admin",
            extra={
                "user_id": user.id,
                "telegram_id": user.telegram_id,
            },
        )


auth_service = AuthService()
