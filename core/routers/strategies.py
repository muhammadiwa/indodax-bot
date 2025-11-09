from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.schemas.common import APIResponse
from core.schemas.strategy import (
    DCARequest,
    GridRequest,
    StrategyExecutionLogRequest,
    StrategyStopRequest,
    TPSLRequest,
)
from core.services.auth_service import auth_service
from core.services.strategy_service import strategy_service
from core.routers.dependencies import require_internal_token

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("/dca")
async def create_dca_strategy(
    payload: DCARequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        strategy = await strategy_service.create_or_update_dca(
            session,
            telegram_id=payload.telegram_id,
            name=payload.name,
            pair=payload.pair,
            amount=payload.amount,
            interval=payload.interval,
            execution_time=payload.execution_time,
            max_runs=payload.max_runs,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=strategy.model_dump())


@router.post("/grid")
async def create_grid_strategy(
    payload: GridRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        strategy = await strategy_service.create_grid(
            session,
            telegram_id=payload.telegram_id,
            name=payload.name,
            pair=payload.pair,
            lower_price=payload.lower_price,
            upper_price=payload.upper_price,
            grid_count=payload.grid_count,
            order_size=payload.order_size,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=strategy.model_dump())


@router.post("/tp-sl")
async def create_tp_sl_strategy(
    payload: TPSLRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        strategy = await strategy_service.create_tp_sl(
            session,
            telegram_id=payload.telegram_id,
            name=payload.name,
            pair=payload.pair,
            entry_price=payload.entry_price,
            take_profit_pct=payload.take_profit_pct,
            stop_loss_pct=payload.stop_loss_pct,
            amount=payload.amount,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=strategy.model_dump())


@router.get("/active")
async def list_active_strategies(
    strategy_type: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[list[dict]]:
    strategies = await strategy_service.list_active_by_type(session, strategy_type)
    return APIResponse(success=True, data=strategies)


@router.get("/{strategy_id}/executions/last")
async def get_last_execution(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[dict | None]:
    execution = await strategy_service.get_last_execution(session, strategy_id)
    return APIResponse(success=True, data=execution.model_dump() if execution else None)


@router.get("/{strategy_id}/executions/count")
async def get_execution_count(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[int]:
    count = await strategy_service.get_execution_count(session, strategy_id)
    return APIResponse(success=True, data=count)


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: int,
    payload: StrategyStopRequest,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[dict]:
    try:
        await auth_service.verify_user_token(session, payload.telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        strategy = await strategy_service.stop_strategy(
            session, telegram_id=payload.telegram_id, strategy_id=strategy_id
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return APIResponse(success=True, data=strategy.model_dump())


@router.post("/{strategy_id}/executions")
async def create_strategy_execution(
    strategy_id: int,
    payload: StrategyExecutionLogRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_internal_token),
) -> APIResponse[dict]:
    execution = await strategy_service.log_execution(
        session,
        strategy_id=strategy_id,
        user_id=payload.user_id,
        status=payload.status,
        detail=payload.detail or {},
    )
    return APIResponse(success=True, data=execution.model_dump())


@router.get("/mine")
async def list_my_strategies(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> APIResponse[list[dict]]:
    try:
        await auth_service.verify_user_token(session, telegram_id, authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    strategies = await strategy_service.list_by_user(session, telegram_id)
    return APIResponse(success=True, data=strategies)
