import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(Exception):
    """Error saat proses enkripsi/dekripsi API key."""


def _get_key() -> bytes:
    secret = os.getenv("APP_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise EncryptionError("APP_SECRET_KEY minimal 32 karakter")
    key = secret.encode("utf-8")
    if len(key) not in {16, 24, 32}:
        key = key[:32].ljust(32, b"0")
    return key


def encrypt_value(value: str) -> Tuple[bytes, bytes]:
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    return nonce, ciphertext


def decrypt_value(nonce: bytes, ciphertext: bytes) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    data = aesgcm.decrypt(nonce, ciphertext, None)
    return data.decode("utf-8")
