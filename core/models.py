from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index, Column, JSON, LargeBinary
from sqlmodel import Field, Relationship, SQLModel


class Users(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(
        sa_column=Column(sa.BigInteger(), unique=True, index=True, nullable=False)
    )
    username: Optional[str] = Field(default=None, index=True)
    full_name: Optional[str] = None
    api_token_hash: Optional[str] = Field(default=None, index=True)
    api_token_expires_at: Optional[datetime] = Field(default=None, index=True)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    keys: list["UserIndodaxKeys"] = Relationship(back_populates="user")
    strategies: list["Strategies"] = Relationship(back_populates="user")


class UserIndodaxKeys(SQLModel, table=True):
    __tablename__ = "user_indodax_keys"
    __table_args__ = (
        Index("ix_user_keys_user_id_active", "user_id", "is_active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    api_key_nonce: Optional[bytes] = Field(
        default=None,
        sa_column=Column("api_key_nonce", LargeBinary(length=12)),
    )
    api_key_ciphertext: bytes = Field(sa_column=Column("api_key_ciphertext", LargeBinary()))
    api_secret_nonce: Optional[bytes] = Field(
        default=None,
        sa_column=Column("api_secret_nonce", LargeBinary(length=12)),
    )
    api_secret_ciphertext: bytes = Field(sa_column=Column("api_secret_ciphertext", LargeBinary()))
    label: Optional[str] = None
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    user: Users = Relationship(back_populates="keys")


class Orders(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
        Index("ix_orders_pair", "pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    indodax_order_id: Optional[str] = Field(default=None, index=True)
    pair: str = Field(index=True)
    side: str
    type: str
    price: Optional[float] = None
    amount: float
    status: str = Field(default="open", index=True)
    is_strategy_order: bool = Field(default=False, nullable=False)
    strategy_id: Optional[int] = Field(default=None, foreign_key="strategies.id")
    raw_request: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    raw_response: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    strategy: Optional["Strategies"] = Relationship(back_populates="orders")
    user: Users = Relationship()


class Strategies(SQLModel, table=True):
    __tablename__ = "strategies"
    __table_args__ = (
        Index("ix_strategies_user_type", "user_id", "type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    type: str = Field(index=True)
    name: str
    pair: str = Field(index=True)
    config_json: dict = Field(sa_column=Column(JSON))
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    user: Users = Relationship(back_populates="strategies")
    executions: list["StrategyExecutions"] = Relationship(back_populates="strategy")
    orders: list[Orders] = Relationship(back_populates="strategy")


class StrategyExecutions(SQLModel, table=True):
    __tablename__ = "strategy_executions"
    __table_args__ = (
        Index("ix_strategy_exec_strategy", "strategy_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key="strategies.id", nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    run_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: str = Field(index=True)
    detail: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    strategy: Strategies = Relationship(back_populates="executions")
    user: Users = Relationship()


class PriceAlerts(SQLModel, table=True):
    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("ix_price_alerts_user_pair", "user_id", "pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    pair: str = Field(index=True)
    target_price: float
    direction: str
    is_triggered: bool = Field(default=False, nullable=False)
    repeat: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    triggered_at: Optional[datetime] = Field(default=None, nullable=True)

    user: Users = Relationship()


class TelemetryEvents(SQLModel, table=True):
    __tablename__ = "telemetry_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    event_type: str = Field(index=True)
    metadata_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: Optional[Users] = Relationship()


class AuditLogs(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    action: str = Field(index=True)
    detail: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: Optional[Users] = Relationship()


SQLModelMetadata = SQLModel.metadata
