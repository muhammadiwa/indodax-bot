"""Utility helpers for encrypting and decrypting user access tokens."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenEncryptionError(Exception):
    """Raised when token encryption/decryption fails."""


@dataclass(slots=True)
class _CryptoMaterial:
    key: bytes


def _derive_key(secret: str) -> _CryptoMaterial:
    if not secret or len(secret) < 32:
        raise TokenEncryptionError("APP_SECRET_KEY minimal 32 karakter")
    key = secret.encode("utf-8")
    if len(key) not in {16, 24, 32}:
        key = key[:32].ljust(32, b"0")
    return _CryptoMaterial(key=key)


def encrypt_token_value(token: str, secret: str) -> str:
    """Encrypt token with AES-GCM and return transport-safe blob."""

    material = _derive_key(secret)
    aesgcm = AESGCM(material.key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, token.encode("utf-8"), None)
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"enc:{payload}"


def decrypt_token_value(value: str, secret: str) -> str:
    """Decrypt token payload and return the original token string."""

    if not value.startswith("enc:"):
        raise TokenEncryptionError("Payload bukan format terenkripsi yang valid")
    payload = value.split(":", 1)[1]
    data = base64.urlsafe_b64decode(payload.encode("ascii"))
    if len(data) <= 12:
        raise TokenEncryptionError("Payload token terenkripsi rusak")
    nonce, ciphertext = data[:12], data[12:]
    material = _derive_key(secret)
    aesgcm = AESGCM(material.key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
