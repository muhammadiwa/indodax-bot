import hashlib
import hmac

import pytest

respx = pytest.importorskip("respx")
from httpx import Response

from core.indodax_private_client import IndodaxPrivateClient


class DummyNonceManager:
    async def get_next_nonce(self, user_id: int) -> int:
        return 123


@pytest.mark.asyncio
@respx.mock
async def test_private_client_signature(monkeypatch):
    monkeypatch.setattr(
        "core.indodax_private_client.nonce_manager", DummyNonceManager()
    )
    route = respx.post("https://indodax.com/tapi").mock(
        return_value=Response(200, json={"success": 1, "return": {"order_id": 1}})
    )
    client = IndodaxPrivateClient()
    result = await client.call(
        user_id=1,
        method="getInfo",
        params={},
        api_key="APIKEY",
        api_secret="SECRET",
    )
    assert route.called
    request = route.calls[0].request
    payload = request.content
    expected_sign = hmac.new(b"SECRET", payload, hashlib.sha512).hexdigest()
    assert request.headers["Key"] == "APIKEY"
    assert request.headers["Sign"] == expected_sign
    assert result["success"] == 1
    await client.close()
