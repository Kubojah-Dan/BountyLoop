"""BountyLoop — Donor profile model.

Represents a food donor establishment (restaurant, grocer, farm, household).
Includes PostGIS Geography(Point, 4326) coordinates for geospatial routing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.models.enums import DonorKind

if TYPE_CHECKING:
    from app.db.models.donation import Donation
    from app.db.models.user import User


class Donor(Base):
    """Food donor establishment entity with geospatial location."""

    __tablename__ = "donors"

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
    kind: Mapped[DonorKind] = mapped_column(
        Enum(DonorKind, name="donor_kind", native_enum=True),
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
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="UTC",
        nullable=False,
    )
    avg_surplus_schedule: Mapped[dict[str, Any] | None] = mapped_column(
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
    user: Mapped[User] = relationship(
        "User",
        back_populates="donor",
    )
    donations: Mapped[list[Donation]] = relationship(
        "Donation",
        back_populates="donor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Donor id={self.id} kind={self.kind} address={self.address[:30]}>"
