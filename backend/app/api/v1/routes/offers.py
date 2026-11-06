"""BountyLoop — Recipient Offers Discovery Endpoints.

Allows food rescue recipients (food banks, shelters, community fridges) to browse
and filter open donations within geographic radius and shelf-life constraints (§6 Phase 6).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import func as geo_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.models import (
    Donation,
    DonationStatus,
    Donor,
    FoodCategory,
    FreshnessGrade,
    Recipient,
    User,
)
from app.db.session import get_db
from app.schemas.claim import OfferRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get(
    "",
    summary="List available surplus offers for recipients",
    response_model=list[OfferRead],
)
async def list_offers(
    radius_km: Annotated[float, Query(ge=0.5, le=100.0)] = 25.0,
    latitude: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    longitude: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    item: Annotated[FoodCategory | None, Query()] = None,
    min_freshness: Annotated[FreshnessGrade | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OfferRead]:
    """Retrieve open surplus food rescue opportunities matching recipient criteria."""
    now = datetime.now(UTC)

    # 1. Resolve user query coordinates
    query_point = None
    if latitude is not None and longitude is not None:
        query_point = geo_func.ST_GeogFromText(f"POINT({longitude} {latitude})")
    else:
        # Check if current user is an onboarding recipient with stored location
        recip_stmt = select(Recipient).where(Recipient.user_id == current_user.id)
        recip_res = await db.execute(recip_stmt)
        recipient = recip_res.scalar_one_or_none()
        if recipient is not None and recipient.location is not None:
            query_point = recipient.location

    # 2. Build base query for open, unexpired, non-reviewed donations
    query = (
        select(Donation)
        .join(Donor, Donation.donor_id == Donor.id)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(
            Donation.status == DonationStatus.open,
            Donation.needs_review.is_(False),
            Donation.expires_at > now,
        )
    )

    if item is not None:
        query = query.where(Donation.item == item)

    if min_freshness is not None:
        fresh_hierarchy = [
            FreshnessGrade.grade_0_spoiled,
            FreshnessGrade.spoiled,
            FreshnessGrade.grade_1_poor,
            FreshnessGrade.grade_2_good,
            FreshnessGrade.grade_3_fresh,
            FreshnessGrade.fresh,
        ]
        try:
            min_idx = fresh_hierarchy.index(min_freshness)
            valid_grades = fresh_hierarchy[min_idx:]
            query = query.where(Donation.freshness.in_(valid_grades))
        except ValueError:
            pass

    # 3. Spatial radius filter if coordinates are available
    if query_point is not None:
        radius_meters = radius_km * 1000.0
        query = query.where(
            geo_func.ST_DWithin(Donor.location, query_point, radius_meters)
        ).order_by(geo_func.ST_Distance(Donor.location, query_point).asc())
    else:
        query = query.order_by(Donation.expires_at.asc())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    donations = result.scalars().all()

    # 4. Map to OfferRead schema
    offers: list[OfferRead] = []
    for don in donations:
        dist_km: float | None = None
        if query_point is not None and don.donor and don.donor.location is not None:
            dist_stmt = select(geo_func.ST_Distance(don.donor.location, query_point))
            dist_res = await db.execute(dist_stmt)
            meters = dist_res.scalar()
            if meters is not None:
                dist_km = round(float(meters) / 1000.0, 2)

        donor_name = None
        donor_address = None
        if don.donor:
            donor_address = don.donor.address
            if don.donor.user:
                donor_name = don.donor.user.display_name or don.donor.user.org_name

        seconds_remaining = (don.expires_at - now).total_seconds()
        hours_remaining = round(max(0.0, seconds_remaining / 3600.0), 1)

        offers.append(
            OfferRead(
                id=don.id,
                donor_id=don.donor_id,
                donor_name=donor_name,
                donor_address=donor_address,
                photo_paths=list(don.photo_paths or []),
                item=don.item,
                freshness=don.freshness,
                est_weight_kg=float(don.est_weight_kg),
                expires_at=don.expires_at,
                hours_remaining=hours_remaining,
                distance_km=dist_km,
                status=don.status,
                created_at=don.created_at,
            )
        )

    return offers
