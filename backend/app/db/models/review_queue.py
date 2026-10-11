"""BountyLoop — Human review queue model.

Holds donations flagged for human intervention due to low inference confidence,
hazard flags (formalin/contamination), or ambiguous recipient matches.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.models.enums import ReviewReason, ReviewStatus

if TYPE_CHECKING:
    from app.db.models.donation import Donation
    from app.db.models.user import User


class ReviewQueue(Base):
    """Review queue item requiring human operator adjudication."""

    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[ReviewReason] = mapped_column(
        Enum(ReviewReason, name="review_reason", native_enum=True),
        nullable=False,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status", native_enum=True),
        default=ReviewStatus.pending,
        server_default=ReviewStatus.pending.value,
        nullable=False,
        index=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    donation: Mapped[Donation] = relationship(
        "Donation",
        back_populates="review_items",
    )
    resolver: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by],
    )

    def __repr__(self) -> str:
        return f"<ReviewQueue id={self.id} donation={self.donation_id} reason={self.reason} status={self.status}>"
