from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.encryption import decrypt_value
from core.indodax_private_client import private_client
from core.repositories.key_repository import user_key_repository
from core.repositories.user_repository import user_repository


class PnLService:
    async def get_realized_pnl(self, session: AsyncSession, telegram_id: int) -> dict[str, Any]:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            return {"pairs": []}
        key = await user_key_repository.get_active_key(session, user.id)
        if not key:
            return {"pairs": []}
        api_key = decrypt_value(key.api_key_nonce, key.api_key_ciphertext)
        api_secret = decrypt_value(key.api_secret_nonce, key.api_secret_ciphertext)
        history = await private_client.call(
            user_id=user.id,
            method="tradeHistory",
            params={"count": 50},
            api_key=api_key,
            api_secret=api_secret,
        )
        trades = history.get("return", {}).get("trades", [])
        pnl: dict[str, float] = {}
        for trade in trades:
            pair = trade.get("pair", "").upper()
            profit = float(trade.get("profit", 0.0))
            pnl[pair] = pnl.get(pair, 0.0) + profit
        return {"pairs": [{"pair": k, "realized_pnl": v} for k, v in pnl.items()]}


pnl_service = PnLService()
