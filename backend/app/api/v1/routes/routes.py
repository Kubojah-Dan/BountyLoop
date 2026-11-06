"""BountyLoop — Route Generation and CVRP Optimization Endpoints (§Master Plan §6 Phase 7).

Provides:
- GET /v1/routes/{claim_id}: Polyline driving geometry between donor and recipient with honest OSRM/estimate labeling.
- POST /v1/routes/optimize: Multi-stop CVRP-lite volunteer rescue route optimizer.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.models import Claim, Donation, User
from app.db.session import get_db
from app.services.matching import extract_lat_lon
from app.services.optimizer import solve_cvrp_lite
from app.services.routing import get_route

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routes", tags=["routes"])


class StopItem(BaseModel):
    """Pickup stop definition for route optimization."""

    id: str | None = None
    name: str | None = None
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    weight_kg: float = Field(default=5.0, ge=0.0)


class RouteOptimizeRequest(BaseModel):
    """Payload to optimize a multi-stop rescue loop."""

    depot_lat: float = Field(..., ge=-90.0, le=90.0)
    depot_lon: float = Field(..., ge=-180.0, le=180.0)
    stops: list[StopItem] = Field(..., min_length=1)
    vehicle_capacity_kg: float = Field(default=200.0, gt=0.0)


@router.get(
    "/{claim_id}",
    summary="Get route polyline and navigation metrics for a claim",
    response_model=dict[str, Any],
)
async def get_claim_route(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve driving route polyline between donor and recipient with honest estimation."""
    stmt = (
        select(Claim)
        .options(
            selectinload(Claim.donation).selectinload(Donation.donor),
            selectinload(Claim.recipient),
        )
        .where(Claim.id == claim_id)
    )
    claim = (await db.execute(stmt)).scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found.",
        )

    donor_loc = claim.donation.donor.location if claim.donation and claim.donation.donor else None
    recip_loc = claim.recipient.location if claim.recipient else None

    donor_coords = extract_lat_lon(donor_loc) or (30.2672, -97.7431)
    recip_coords = extract_lat_lon(recip_loc) or (30.2750, -97.7400)

    route_data = await get_route(
        lat1=donor_coords[0],
        lon1=donor_coords[1],
        lat2=recip_coords[0],
        lon2=recip_coords[1],
    )

    source = route_data.get("source", "estimate")
    return {
        "claim_id": str(claim.id),
        "donor_id": str(claim.donation.donor_id) if claim.donation else None,
        "recipient_id": str(claim.recipient_id),
        "donor_coordinates": {"lat": donor_coords[0], "lon": donor_coords[1]},
        "recipient_coordinates": {"lat": recip_coords[0], "lon": recip_coords[1]},
        "distance_m": route_data.get("distance_m", 0.0),
        "duration_s": route_data.get("duration_s", 0.0),
        "source": source,
        "route_source": source,
        "geometry": route_data.get("geometry"),
    }


@router.post(
    "/optimize",
    summary="Optimize multi-stop rescue route (CVRP-lite)",
    response_model=dict[str, Any],
)
async def optimize_rescue_route(
    payload: RouteOptimizeRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Solve multi-stop CVRP-lite route minimizing transit distance."""
    depot = (payload.depot_lat, payload.depot_lon)
    stops_data = [s.model_dump() for s in payload.stops]
    solution = solve_cvrp_lite(
        depot=depot,
        stops=stops_data,
        vehicle_capacity_kg=payload.vehicle_capacity_kg,
    )
    return solution
