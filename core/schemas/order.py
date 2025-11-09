from typing import Optional

from typing import Optional

from pydantic import BaseModel, Field, validator


class CreateOrderRequest(BaseModel):
    telegram_id: int
    pair: str
    side: str
    type: str = Field(..., pattern="^(market|limit)$")
    amount: float
    price: Optional[float] = None
    is_strategy_order: bool = False
    strategy_id: Optional[int] = None

    @validator("side")
    def validate_side(cls, value: str) -> str:
        if value not in {"buy", "sell"}:
            raise ValueError("side harus buy atau sell")
        return value


class OrderResponse(BaseModel):
    id: int
    indodax_order_id: Optional[str]
    pair: str
    side: str
    type: str
    price: Optional[float]
    amount: float
    status: str
    created_at: Optional[str] = None
    is_strategy_order: bool
    strategy_id: Optional[int]


class OrderSyncRequest(BaseModel):
    telegram_ids: list[int] | None = None


class OrderSyncResponse(BaseModel):
    updated: int
    details: list[dict[str, str]]
