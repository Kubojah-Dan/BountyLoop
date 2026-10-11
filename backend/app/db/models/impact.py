"""BountyLoop — Impact log model.

Records environmental and social impact metrics per successfully rescued donation
(kg rescued, meals equivalent, CO2e avoided in kg).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.donation import Donation


class ImpactLog(Base):
    """Environmental and nutritional impact record for a rescued donation."""

    __tablename__ = "impact_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    kg_rescued: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    meals_equivalent: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    co2e_avoided_kg: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )
    method_version: Mapped[str] = mapped_column(
        String(32),
        default="v1.0",
        nullable=False,
    )

    # Relationships
    donation: Mapped[Donation] = relationship(
        "Donation",
        back_populates="impact_log",
    )

    def __repr__(self) -> str:
        return f"<ImpactLog id={self.id} donation={self.donation_id} kg={self.kg_rescued} co2e={self.co2e_avoided_kg}>"
