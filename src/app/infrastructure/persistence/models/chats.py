"""SQLAlchemy models for official Business connections and chats."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.access import Base


class BusinessConnectionModel(Base):
    __tablename__ = "business_connections"

    connection_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
    )
    owner_telegram_id: Mapped[int] = mapped_column(BigInteger)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CustomerChatModel(Base):
    __tablename__ = "customer_chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
