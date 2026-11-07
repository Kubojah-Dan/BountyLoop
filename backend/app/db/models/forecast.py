"""BountyLoop — Donor surplus forecasts database model."""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.donor import Donor


class DonorSurplusForecast(Base):
    """Stores modeled forward surplus predictions for donors.

    NOTE: ALL predictions must have is_synthetic=True until at least 8 weeks
    of empirical pilot records are used to train production models.
    """

    __tablename__ = "donor_surplus_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "donor_id",
            "forecast_date",
            "model_version",
            name="uq_donor_forecast_date_model",
        ),
    )

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
    forecast_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    predicted_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence_lower_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence_upper_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="sarimax_v1",
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    donor: Mapped[Donor] = relationship("Donor", foreign_keys=[donor_id])
