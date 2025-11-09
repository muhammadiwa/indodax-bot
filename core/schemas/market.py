from pydantic import BaseModel


class OrderBookEntry(BaseModel):
    price: float
    amount: float


class OrderBookSummary(BaseModel):
    bids: list[OrderBookEntry]
    asks: list[OrderBookEntry]


class PriceResponse(BaseModel):
    pair: str
    price: float
    order_book: OrderBookSummary


class TickerResponse(BaseModel):
    tickers: dict
