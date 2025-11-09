from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.schemas.common import APIResponse
from core.schemas.order import (
    CreateOrderRequest,
    OrderResponse,
    OrderSyncRequest,
    OrderSyncResponse,
)
from core.services.auth_service import auth_service
from core.services.order_service import order_service
from core.routers.dependencies import is_internal_request, require_internal_token

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=APIResponse[OrderResponse])
async def create_order(
    payload: CreateOrderRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
    is_internal: bool = Depends(is_internal_request),
) -> APIResponse[OrderResponse]:
    if not is_internal:
        try:
            await auth_service.verify_user_token(
                session, payload.telegram_id, authorization
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        order = await order_service.create_order(
            session,
            telegram_id=payload.telegram_id,
            pair=payload.pair,
            side=payload.side,
            order_type=payload.type,
            amount=payload.amount,
            price=payload.price,
            is_strategy_order=payload.is_strategy_order,
            strategy_id=payload.strategy_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=OrderResponse.model_validate(order.model_dump()))


@router.get("/open", response_model=APIResponse[list[OrderResponse]])
async def get_open_orders(
    telegram_id: int,
    pair: str | None = None,
    strategy_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
    is_internal: bool = Depends(is_internal_request),
) -> APIResponse[list[OrderResponse]]:
    if not is_internal:
        try:
            await auth_service.verify_user_token(session, telegram_id, authorization)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    orders = await order_service.get_open_orders(
        session,
        telegram_id,
        pair=pair,
        strategy_id=strategy_id,
    )
    data = [OrderResponse.model_validate(order.model_dump()) for order in orders]
    return APIResponse(success=True, data=data)


@router.post("/{order_id}/cancel", response_model=APIResponse[OrderResponse])
async def cancel_order(
    order_id: int,
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
    is_internal: bool = Depends(is_internal_request),
) -> APIResponse[OrderResponse]:
    if not is_internal:
        try:
            await auth_service.verify_user_token(session, telegram_id, authorization)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        order = await order_service.cancel_order(session, telegram_id, order_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=OrderResponse.model_validate(order.model_dump()))


@router.post("/sync-status", response_model=APIResponse[OrderSyncResponse])
async def sync_order_status(
    payload: OrderSyncRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[OrderSyncResponse]:
    result = await order_service.sync_open_orders(
        session, telegram_ids=payload.telegram_ids
    )
    return APIResponse(success=True, data=result)
