from pydantic import BaseModel, Field


class AlertRequest(BaseModel):
    telegram_id: int
    pair: str
    target_price: float
    direction: str = Field(description="up untuk >=, down untuk <=")
    repeat: bool = False
