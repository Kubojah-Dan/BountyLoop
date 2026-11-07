"""BountyLoop — SMS message audit model.

Tracks outbound alerts and inbound webhook SMS messages,
enforcing delivery audits and the SMS_DAILY_CAP.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.claim import Claim
    from app.db.models.user import User


class SmsMessage(Base):
    """SMS message record for outbound dispatch and inbound webhook events."""

    __tablename__ = "sms_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="outbound",
    )  # "outbound" or "inbound"
    to_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    from_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="sent",
        index=True,
    )  # "sent", "delivered", "failed", "capped", "received"
    sid: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user: Mapped[User | None] = relationship("User", foreign_keys=[user_id])
    claim: Mapped[Claim | None] = relationship("Claim", foreign_keys=[claim_id])
