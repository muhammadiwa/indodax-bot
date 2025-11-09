"""initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2024-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "user_indodax_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("api_key_nonce", sa.LargeBinary(length=12), nullable=True),
        sa.Column("api_key_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("api_secret_nonce", sa.LargeBinary(length=12), nullable=True),
        sa.Column("api_secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_user_keys_user_id_active",
        "user_indodax_keys",
        ["user_id", "is_active"],
    )

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pair", sa.String(length=50), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_strategies_user_type", "strategies", ["user_id", "type"])
    op.create_index("ix_strategies_pair", "strategies", ["pair"])
    op.create_index("ix_strategies_type", "strategies", ["type"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("indodax_order_id", sa.String(length=64), nullable=True),
        sa.Column("pair", sa.String(length=50), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=True),
        sa.Column("amount", sa.Numeric(24, 10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("is_strategy_order", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("raw_request", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_orders_user_status", "orders", ["user_id", "status"])
    op.create_index("ix_orders_pair", "orders", ["pair"])
    op.create_index("ix_orders_indodax_order_id", "orders", ["indodax_order_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "strategy_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_strategy_exec_strategy", "strategy_executions", ["strategy_id"])
    op.create_index("ix_strategy_exec_status", "strategy_executions", ["status"])

    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("pair", sa.String(length=50), nullable=False),
        sa.Column("target_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("repeat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_price_alerts_user_pair", "price_alerts", ["user_id", "pair"])
    op.create_index("ix_price_alerts_pair", "price_alerts", ["pair"])

    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_telemetry_events_event_type", "telemetry_events", ["event_type"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_ip", "audit_logs", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_ip", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_telemetry_events_event_type", table_name="telemetry_events")
    op.drop_table("telemetry_events")

    op.drop_index("ix_price_alerts_pair", table_name="price_alerts")
    op.drop_index("ix_price_alerts_user_pair", table_name="price_alerts")
    op.drop_table("price_alerts")

    op.drop_index("ix_strategy_exec_status", table_name="strategy_executions")
    op.drop_index("ix_strategy_exec_strategy", table_name="strategy_executions")
    op.drop_table("strategy_executions")

    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_indodax_order_id", table_name="orders")
    op.drop_index("ix_orders_pair", table_name="orders")
    op.drop_index("ix_orders_user_status", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_strategies_type", table_name="strategies")
    op.drop_index("ix_strategies_pair", table_name="strategies")
    op.drop_index("ix_strategies_user_type", table_name="strategies")
    op.drop_table("strategies")

    op.drop_index("ix_user_keys_user_id_active", table_name="user_indodax_keys")
    op.drop_table("user_indodax_keys")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
