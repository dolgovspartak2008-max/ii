"""Add a global AI reply switch to tenants."""

import sqlalchemy as sa

from alembic import op

revision = "20260716_05"
down_revision = "20260716_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("tenants", "ai_enabled")
