"""BountyLoop — Environmental & Social Impact Routes (§Master Plan §6 Phase 10).

Provides auditable endpoints for impact summaries, timeseries binning,
CSV data exports, database reconciliation audits, and scientific methodology disclosures.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.impact import (
    ImpactMethodologyRead,
    ImpactReconciliationRead,
    ImpactSummaryRead,
    ImpactTimeseriesRead,
)
from app.services.impact import (
    generate_impact_csv,
    get_impact_factors_metadata,
    get_impact_summary,
    get_impact_timeseries,
    reconcile_impact,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/impact", tags=["Impact Measurement & Methodology"])


@router.get(
    "/methodology",
    response_model=ImpactMethodologyRead,
    summary="Impact methodology, factors, and scientific citations",
)
async def get_methodology() -> ImpactMethodologyRead:
    """Return the active impact methodology specifications and citations.

    Explicitly labels avoided greenhouse gas emissions as an UNVERIFIED modeled estimate.
    """
    return get_impact_factors_metadata()


@router.get(
    "/summary",
    response_model=ImpactSummaryRead,
    summary="Aggregate social and environmental impact metrics",
)
async def get_summary(
    start_date: datetime | None = Query(None, description="Filter from start date (ISO 8601)"),
    end_date: datetime | None = Query(None, description="Filter to end date (ISO 8601)"),
    donor_id: uuid.UUID | None = Query(None, description="Optional donor UUID filter"),
    recipient_id: uuid.UUID | None = Query(None, description="Optional recipient UUID filter"),
    db: AsyncSession = Depends(get_db),
) -> ImpactSummaryRead:
    """Return total food rescued (kg), meal equivalents, and estimated avoided GHG emissions."""
    return await get_impact_summary(
        db=db,
        start_date=start_date,
        end_date=end_date,
        donor_id=donor_id,
        recipient_id=recipient_id,
    )


@router.get(
    "/timeseries",
    response_model=ImpactTimeseriesRead,
    summary="Historical impact metrics binned by temporal interval",
)
async def get_timeseries(
    interval: Literal["day", "week", "month"] = Query(
        "day", description="Temporal aggregation bucket"
    ),
    start_date: datetime | None = Query(None, description="Filter from start date"),
    end_date: datetime | None = Query(None, description="Filter to end date"),
    donor_id: uuid.UUID | None = Query(None, description="Optional donor UUID filter"),
    recipient_id: uuid.UUID | None = Query(None, description="Optional recipient UUID filter"),
    db: AsyncSession = Depends(get_db),
) -> ImpactTimeseriesRead:
    """Return historical impact metrics grouped by day, week, or month."""
    return await get_impact_timeseries(
        db=db,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        donor_id=donor_id,
        recipient_id=recipient_id,
    )


@router.get(
    "/export/csv",
    summary="Export all historical impact records to CSV",
    response_class=Response,
)
async def export_csv(
    start_date: datetime | None = Query(None, description="Filter from start date"),
    end_date: datetime | None = Query(None, description="Filter to end date"),
    donor_id: uuid.UUID | None = Query(None, description="Optional donor UUID filter"),
    recipient_id: uuid.UUID | None = Query(None, description="Optional recipient UUID filter"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download a CSV containing granular impact transaction records."""
    csv_data = await generate_impact_csv(
        db=db,
        start_date=start_date,
        end_date=end_date,
        donor_id=donor_id,
        recipient_id=recipient_id,
    )
    filename = f"bountyloop_impact_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/reconciliation",
    response_model=ImpactReconciliationRead,
    summary="Audit database reconciliation between completed claims, donations, and impact records",
)
async def get_reconciliation(
    db: AsyncSession = Depends(get_db),
) -> ImpactReconciliationRead:
    """Perform mathematical and row-count reconciliation across the food rescue ledger."""
    return await reconcile_impact(db)
