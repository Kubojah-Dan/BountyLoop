"""BountyLoop — Claim model.

Represents an offer or match between a surplus donation and a recipient,
scored by the matching engine with fair-allocation weights.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.models.enums import ClaimStatus

if TYPE_CHECKING:
    from app.db.models.donation import Donation
    from app.db.models.recipient import Recipient


class Claim(Base):
    """Claim entity representing recipient offer and pickup lifecycle."""

    __tablename__ = "claims"

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
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status", native_enum=True),
        default=ClaimStatus.offered,
        server_default=ClaimStatus.offered.value,
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    proof_photo_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # Relationships
    donation: Mapped[Donation] = relationship(
        "Donation",
        back_populates="claims",
    )
    recipient: Mapped[Recipient] = relationship(
        "Recipient",
        back_populates="claims",
    )

    def __repr__(self) -> str:
        return f"<Claim id={self.id} donation={self.donation_id} recipient={self.recipient_id} status={self.status}>"
