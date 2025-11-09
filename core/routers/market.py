from fastapi import APIRouter, HTTPException
import httpx

from core.indodax_public_client import public_client
from core.schemas.common import APIResponse
from core.schemas.market import (
    OrderBookEntry,
    OrderBookSummary,
    PriceResponse,
    TickerResponse,
)

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/tickers", response_model=APIResponse[TickerResponse])
async def get_tickers() -> APIResponse[TickerResponse]:
    data = await public_client.get_tickers()
    return APIResponse(success=True, data=TickerResponse(tickers=data.get("tickers", {})))


@router.get("/price/{pair}", response_model=APIResponse[PriceResponse])
async def get_price(pair: str) -> APIResponse[PriceResponse]:
    try:
        ticker = await public_client.get_ticker(pair)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gagal mengambil harga") from exc
    try:
        order_book = await public_client.get_order_book(pair, depth=20)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gagal mengambil order book") from exc
    price = float(ticker.get("ticker", {}).get("last", 0.0))

    def _parse_levels(levels: list[list[str | float]]) -> list[OrderBookEntry]:
        top_levels = levels[:5]
        parsed: list[OrderBookEntry] = []
        for entry in top_levels:
            if len(entry) < 2:
                continue
            price_val, amount_val = entry[0], entry[1]
            try:
                price_f = float(price_val)
                amount_f = float(amount_val)
            except (TypeError, ValueError):
                continue
            parsed.append(OrderBookEntry(price=price_f, amount=amount_f))
        return parsed

    summary = OrderBookSummary(
        bids=_parse_levels(order_book.get("buy", [])),
        asks=_parse_levels(order_book.get("sell", [])),
    )
    return APIResponse(
        success=True,
        data=PriceResponse(pair=pair.upper(), price=price, order_book=summary),
    )
