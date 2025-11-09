"""add api token hash to users

Revision ID: 0002_add_user_token_hash
Revises: 0001_initial
Create Date: 2024-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_user_token_hash"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("api_token_hash", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_users_api_token_hash", "users", ["api_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_api_token_hash", table_name="users")
    op.drop_column("users", "api_token_hash")
