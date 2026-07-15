"""Create access applications table."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260715_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_telegram_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_access_applications_telegram_id",
        "access_applications",
        ["telegram_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_applications_telegram_id",
        table_name="access_applications",
    )
    op.drop_table("access_applications")
