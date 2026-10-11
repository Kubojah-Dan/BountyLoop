"""BountyLoop — Donation model.

Represents surplus food batches submitted by donors, assessed by CV inference
(item taxonomy, freshness grade, hazard safety gate), and routed by the agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.models.enums import DonationStatus, FoodCategory, FreshnessGrade, HazardFlag

if TYPE_CHECKING:
    from app.db.models.agent_event import AgentEvent
    from app.db.models.claim import Claim
    from app.db.models.donor import Donor
    from app.db.models.impact import ImpactLog
    from app.db.models.review_queue import ReviewQueue


class Donation(Base):
    """Food donation entity with CV predictions and lifecycle status."""

    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_paths: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )
    item: Mapped[FoodCategory] = mapped_column(
        Enum(FoodCategory, name="food_category", native_enum=True),
        nullable=False,
    )
    item_confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    freshness: Mapped[FreshnessGrade] = mapped_column(
        Enum(FreshnessGrade, name="freshness_grade", native_enum=True),
        nullable=False,
    )
    freshness_confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    hazard_flag: Mapped[HazardFlag] = mapped_column(
        Enum(HazardFlag, name="hazard_flag", native_enum=True),
        default=HazardFlag.none,
        server_default=HazardFlag.none.value,
        nullable=False,
    )
    est_weight_kg: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status", native_enum=True),
        default=DonationStatus.draft,
        server_default=DonationStatus.draft.value,
        nullable=False,
        index=True,
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    model_versions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    donor: Mapped[Donor] = relationship(
        "Donor",
        back_populates="donations",
    )
    claims: Mapped[list[Claim]] = relationship(
        "Claim",
        back_populates="donation",
        cascade="all, delete-orphan",
    )
    impact_log: Mapped[ImpactLog | None] = relationship(
        "ImpactLog",
        back_populates="donation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    agent_events: Mapped[list[AgentEvent]] = relationship(
        "AgentEvent",
        back_populates="donation",
    )
    review_items: Mapped[list[ReviewQueue]] = relationship(
        "ReviewQueue",
        back_populates="donation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Donation id={self.id} item={self.item} status={self.status} weight={self.est_weight_kg}kg>"
