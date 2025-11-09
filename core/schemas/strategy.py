from typing import Optional

from pydantic import BaseModel, Field


class DCARequest(BaseModel):
    telegram_id: int
    name: str = Field(default="DCA")
    pair: str
    amount: float
    interval: str = Field(description="Contoh: daily, weekly, hourly")
    execution_time: str = Field(description="Format HH:MM (24 jam)")
    max_runs: Optional[int] = None


class StrategyStopRequest(BaseModel):
    telegram_id: int
    strategy_id: int


class StrategyExecutionLogRequest(BaseModel):
    user_id: int
    status: str
    detail: dict | None = None


class GridRequest(BaseModel):
    telegram_id: int
    name: str = Field(default="Grid Strategy")
    pair: str
    lower_price: float
    upper_price: float
    grid_count: int = Field(ge=2, le=100)
    order_size: float


class TPSLRequest(BaseModel):
    telegram_id: int
    name: str = Field(default="TP/SL")
    pair: str
    entry_price: float
    take_profit_pct: float = Field(gt=0)
    stop_loss_pct: float = Field(gt=0)
    amount: float
