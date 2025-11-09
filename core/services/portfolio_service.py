from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.encryption import decrypt_value
from core.indodax_private_client import private_client
from core.indodax_public_client import public_client
from core.repositories.key_repository import user_key_repository
from core.repositories.user_repository import user_repository


class PortfolioService:
    async def get_portfolio(self, session: AsyncSession, telegram_id: int) -> dict[str, Any]:
        user = await user_repository.get_by_telegram_id(session, telegram_id)
        if not user:
            return {"balances": []}
        key = await user_key_repository.get_active_key(session, user.id)
        if not key:
            return {"balances": []}
        api_key = decrypt_value(key.api_key_nonce, key.api_key_ciphertext)
        api_secret = decrypt_value(key.api_secret_nonce, key.api_secret_ciphertext)
        info = await private_client.call(
            user_id=user.id,
            method="getInfo",
            params={},
            api_key=api_key,
            api_secret=api_secret,
        )
        balances = info.get("return", {}).get("balance", {})
        tickers = await public_client.get_tickers()
        portfolio = []
        total_value = 0.0
        for asset, amount in balances.items():
            if not amount:
                continue
            pair = f"{asset.upper()}IDR"
            ticker = tickers.get("tickers", {}).get(pair.lower())
            price = float(ticker.get("last")) if ticker else 0.0
            value_idr = float(amount) * price
            portfolio.append(
                {
                    "asset": asset.upper(),
                    "amount": float(amount),
                    "price": price,
                    "value_idr": value_idr,
                }
            )
            total_value += value_idr
        for item in portfolio:
            item["allocation_pct"] = (
                (item["value_idr"] / total_value) * 100 if total_value else 0.0
            )
        return {"balances": portfolio, "total_value_idr": total_value}


portfolio_service = PortfolioService()
