"""BountyLoop — Recipient organization model.

Represents charities, food banks, shelters, and community fridges.
Includes PostGIS Geography(Point, 4326), daily capacity, accepted items,
cold-chain capabilities, and dynamic urgency weighting.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.models.enums import RecipientOrgType

if TYPE_CHECKING:
    from app.db.models.claim import Claim
    from app.db.models.user import User


class Recipient(Base):
    """Food recipient organization entity with geospatial location and rescue capacity."""

    __tablename__ = "recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    org_type: Mapped[RecipientOrgType] = mapped_column(
        Enum(RecipientOrgType, name="recipient_org_type", native_enum=True),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    capacity_kg_per_day: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    accepted_items: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )
    cold_chain: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    operating_hours: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    urgency_weight: Mapped[float] = mapped_column(
        Numeric(5, 2),
        server_default="1.0",
        default=1.0,
        nullable=False,
    )
    is_accepting: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="recipient",
    )
    claims: Mapped[list[Claim]] = relationship(
        "Claim",
        back_populates="recipient",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recipient id={self.id} org_type={self.org_type} capacity={self.capacity_kg_per_day}kg>"
