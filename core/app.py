from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.routers import (
    alerts,
    auth,
    market,
    notifications,
    orders,
    portfolio,
    pnl,
    strategies,
    system,
)
from core.services.notification_service import notification_service

settings = get_settings()

app = FastAPI(title="Indodax Trading Core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(market.router)
app.include_router(orders.router)
app.include_router(portfolio.router)
app.include_router(pnl.router)
app.include_router(strategies.router)
app.include_router(alerts.router)
app.include_router(system.router)
app.include_router(notifications.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.on_event("startup")
async def startup() -> None:
    await notification_service.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    await notification_service.stop()
