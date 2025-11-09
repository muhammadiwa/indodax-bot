"""add api token expiry

Revision ID: 0003_add_token_expiry
Revises: 0002_add_user_token_hash
Create Date: 2024-01-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_add_token_expiry"
down_revision: str = "0002_add_user_token_hash"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("api_token_expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_users_api_token_expires_at",
        "users",
        ["api_token_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_api_token_expires_at", table_name="users")
    op.drop_column("users", "api_token_expires_at")
