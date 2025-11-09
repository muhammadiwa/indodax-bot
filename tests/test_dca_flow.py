import pytest

pendulum = pytest.importorskip("pendulum")

from worker.tasks import dca


class DummyCoreAPIClient:
    def __init__(self, strategies: list[dict] | None = None) -> None:
        self.requests: list[tuple[str, dict, bool]] = []
        self.last_execution_response = {"data": None}
        self.count_response = {"data": 0}
        self.strategies = strategies or []

    async def get(
        self,
        path: str,
        params: dict | None = None,
        *,
        internal: bool = False,
    ):
        if path.endswith("/executions/last"):
            return self.last_execution_response
        if path.endswith("/executions/count"):
            return self.count_response
        if path == "/api/strategies/active":
            return {"data": self.strategies}
        raise AssertionError(f"Unhandled GET path {path}")

    async def post(
        self,
        path: str,
        payload: dict,
        *,
        internal: bool = False,
    ):
        self.requests.append((path, payload, internal))
        return {"success": True, "data": {}}


class DummySettings:
    scheduler_timezone = "UTC"
    worker_poll_interval_seconds = 30


@pytest.mark.asyncio
async def test_dca_should_run(monkeypatch):
    strategy = {
        "id": 1,
        "user_id": 10,
        "telegram_id": 900,
        "pair": "BTCIDR",
        "config_json": {
            "interval": "daily",
            "execution_time": "00:00",
            "amount": 0.001,
        },
    }
    client = DummyCoreAPIClient(strategies=[strategy])
    monkeypatch.setattr(dca, "core_api_client", client)
    monkeypatch.setattr(dca, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(dca.pendulum, "now", lambda tz: pendulum.datetime(2024, 1, 1, 1, 0, tz=tz))

    await dca.run_dca_strategies()
    assert any(
        request[0] == "/api/orders" for request in client.requests
    ), "Order harus dibuat untuk strategi DCA"
