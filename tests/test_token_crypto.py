import pytest

pytest.importorskip("cryptography")

from bot.utils.crypto import (
    TokenEncryptionError,
    decrypt_token_value,
    encrypt_token_value,
)


def test_encrypt_decrypt_roundtrip():
    secret = "a" * 32
    token = "sample-token"
    payload = encrypt_token_value(token, secret)
    assert payload.startswith("enc:")
    assert decrypt_token_value(payload, secret) == token


def test_decrypt_invalid_payload():
    secret = "b" * 32
    with pytest.raises(TokenEncryptionError):
        decrypt_token_value("invalid", secret)
