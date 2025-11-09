import pytest

pendulum = pytest.importorskip("pendulum")

from worker.tasks import alerts, grid, tp_sl


class DummyCoreClient:
    def __init__(self, responses):
        self._responses = responses
        self.posts = []
        self.get_calls = []

    async def get(self, path, params=None, *, internal=False):
        self.get_calls.append((path, params, internal))
        handler = self._responses.get(("GET", path))
        if callable(handler):
            return handler(params)
        return handler

    async def post(self, path, payload, *, internal=False):
        self.posts.append((path, payload, internal))
        handler = self._responses.get(("POST", path))
        if callable(handler):
            return handler(payload)
        return handler or {"success": True}


@pytest.mark.asyncio
async def test_grid_skips_existing_orders(monkeypatch):
    strategy = {
        "id": 1,
        "user_id": 2,
        "telegram_id": 3,
        "pair": "BTCIDR",
        "config_json": {
            "lower_price": 100_000_000,
            "upper_price": 200_000_000,
            "grid_count": 2,
            "order_size": 0.01,
        },
    }
    existing_orders = [
        {
            "side": "buy",
            "price": 100_000_000.0,
            "is_strategy_order": True,
            "strategy_id": 1,
        }
    ]

    client = DummyCoreClient(
        {
            ("GET", "/api/strategies/active"): lambda params: {"data": [strategy]},
            ("GET", "/api/orders/open"): lambda params: {"data": existing_orders},
        }
    )
    monkeypatch.setattr(grid, "core_api_client", client)

    async def always_true() -> bool:
        return True

    async def noop_trigger(*_args, **_kwargs) -> None:
        return None

    async def fake_send_notification(*args, **kwargs):
        return None

    monkeypatch.setattr(grid, "ensure_trading_active", always_true)
    monkeypatch.setattr(grid, "send_notification", fake_send_notification)
    monkeypatch.setattr(grid, "trigger_deadman", noop_trigger)
    monkeypatch.setattr(grid.pendulum, "now", lambda tz: pendulum.datetime(2024, 1, 1, tz=tz))

    await grid.run_grid_strategies()

    order_posts = [item for item in client.posts if item[0] == "/api/orders"]
    assert len(order_posts) == 2
    for _, payload, _ in order_posts:
        assert payload["is_strategy_order"] is True
        assert payload["strategy_id"] == strategy["id"]
    # Ensure internal token used for worker-only endpoints
    assert all(call[2] is True for call in client.get_calls if call[0] != "/api/orders")


@pytest.mark.asyncio
async def test_grid_cancels_stale_orders(monkeypatch):
    strategy = {
        "id": 2,
        "user_id": 4,
        "telegram_id": 5,
        "pair": "ETHIDR",
        "config_json": {
            "lower_price": 10_000_000,
            "upper_price": 15_000_000,
            "grid_count": 2,
            "order_size": 1.5,
        },
    }
    stale_orders = [
        {
            "id": 77,
            "side": "buy",
            "price": 9_000_000.0,
            "is_strategy_order": True,
            "strategy_id": 2,
        }
    ]

    client = DummyCoreClient(
        {
            ("GET", "/api/strategies/active"): lambda params: {"data": [strategy]},
            ("GET", "/api/orders/open"): lambda params: {"data": stale_orders},
        }
    )
    monkeypatch.setattr(grid, "core_api_client", client)

    async def always_true() -> bool:
        return True

    async def noop_trigger(*_args, **_kwargs) -> None:
        return None

    async def fake_send_notification(*_args, **_kwargs):
        return None

    monkeypatch.setattr(grid, "ensure_trading_active", always_true)
    monkeypatch.setattr(grid, "send_notification", fake_send_notification)
    monkeypatch.setattr(grid, "trigger_deadman", noop_trigger)
    monkeypatch.setattr(grid.pendulum, "now", lambda tz: pendulum.datetime(2024, 1, 1, tz=tz))

    await grid.run_grid_strategies()

    cancel_calls = [item for item in client.posts if item[0].endswith("/cancel")]
    assert cancel_calls, "Order kadaluarsa harus dibatalkan"
    for _, payload, internal in cancel_calls:
        assert internal is True
        assert payload["telegram_id"] == strategy["telegram_id"]


@pytest.mark.asyncio
async def test_tp_sl_marks_orders_and_logs(monkeypatch):
    strategy = {
        "id": 5,
        "user_id": 9,
        "telegram_id": 7,
        "pair": "ETHIDR",
        "config_json": {
            "entry_price": 10_000,
            "take_profit_pct": 10,
            "stop_loss_pct": 5,
            "amount": 0.5,
        },
    }
    client = DummyCoreClient(
        {
            ("GET", "/api/strategies/active"): lambda params: {"data": [strategy]},
        }
    )
    monkeypatch.setattr(tp_sl, "core_api_client", client)

    async def ensure_true() -> bool:
        return True

    async def fake_price(pair):
        return 11_500

    async def noop_notify(*_args, **_kwargs):
        return None

    async def noop_deadman(*_args, **_kwargs):
        return None

    monkeypatch.setattr(tp_sl, "ensure_trading_active", ensure_true)
    monkeypatch.setattr(tp_sl.price_feed, "get_price", fake_price)
    monkeypatch.setattr(tp_sl, "send_notification", noop_notify)
    monkeypatch.setattr(tp_sl, "trigger_deadman", noop_deadman)
    monkeypatch.setattr(tp_sl.pendulum, "now", lambda tz: pendulum.datetime(2024, 1, 1, tz=tz))

    await tp_sl.monitor_tp_sl()

    order_posts = [item for item in client.posts if item[0] == "/api/orders"]
    assert order_posts, "Order market harus dibuat"
    _, payload, _ = order_posts[0]
    assert payload["is_strategy_order"] is True
    assert payload["strategy_id"] == strategy["id"]
    log_posts = [item for item in client.posts if "executions" in item[0]]
    assert log_posts and log_posts[0][2] is True


@pytest.mark.asyncio
async def test_alerts_use_internal_token(monkeypatch):
    alerts_data = [
        {
            "id": 10,
            "telegram_id": 42,
            "pair": "BTCIDR",
            "target_price": 100,
            "direction": "up",
            "repeat": False,
        }
    ]
    client = DummyCoreClient(
        {
            ("GET", "/api/alerts/active"): {"data": alerts_data},
            ("POST", "/api/alerts/10/trigger"): {"success": True},
        }
    )
    monkeypatch.setattr(alerts, "core_api_client", client)

    async def fake_price_alert(_pair):
        return 150

    async def noop_send(*_args, **_kwargs):
        return None

    monkeypatch.setattr(alerts.price_feed, "get_price", fake_price_alert)
    monkeypatch.setattr(alerts, "send_notification", noop_send)
    monkeypatch.setattr(alerts.pendulum, "now", lambda tz: pendulum.datetime(2024, 1, 1, tz=tz))

    await alerts.check_price_alerts()

    assert client.get_calls[0][2] is True
    trigger_calls = [post for post in client.posts if post[0].endswith("/trigger")]
    assert trigger_calls and trigger_calls[0][2] is True
