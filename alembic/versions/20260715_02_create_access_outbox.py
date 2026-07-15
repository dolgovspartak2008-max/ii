"""Create durable access notification outbox."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260715_02"
down_revision = "20260715_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_access_outbox_events_event_type",
        "access_outbox_events",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_outbox_events_event_type",
        table_name="access_outbox_events",
    )
    op.drop_table("access_outbox_events")
