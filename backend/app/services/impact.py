"""BountyLoop — Environmental & Social Impact Calculation Service.

Pure functions and aggregation queries implementing defensible surplus rescue metrics:
- meals_equivalent: kg / MEAL_KG_FACTOR (default 1.2 kg per meal equivalent;
  reference: USDA Economic Research Service / ReFED food redistribution conversion standard).
- co2e_avoided: kg * IMPACT_CO2E_FACTOR (default 2.5 kg CO2e per kg food waste avoided;
  reference: UNEP Food Waste Index / EPA Waste Reduction Model [WARM], marked UNVERIFIED estimate).
- Auditable aggregation, timeseries binning, CSV reporting, and reconciliation verification (§6 Phase 10).
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models.claim import Claim
from app.db.models.donation import Donation
from app.db.models.donor import Donor
from app.db.models.enums import ClaimStatus, DonationStatus
from app.db.models.impact import ImpactLog
from app.db.models.recipient import Recipient
from app.schemas.impact import (
    ImpactFactorDetail,
    ImpactMethodologyRead,
    ImpactReconciliationRead,
    ImpactSummaryRead,
    ImpactTimeseriesPoint,
    ImpactTimeseriesRead,
)

logger = logging.getLogger(__name__)

IMPACT_METHOD_VERSION = "v1"

CO2E_DISCLAIMER = (
    "Greenhouse gas emissions avoided are modeled estimates based on landfill diversion factors "
    "(EPA WARM v15 / UNEP 2021). Not laboratory-measured."
)


def get_impact_factors_metadata() -> ImpactMethodologyRead:
    """Return configured impact factors, citations, and disclosure status."""
    settings = get_settings()
    meal_factor = ImpactFactorDetail(
        factor_name="meal_kg_factor",
        value=settings.meal_kg_factor,
        unit="kg/meal",
        source="USDA Economic Research Service (ERS) / FAO / ReFED Standard",
        status="verified_standard",
        description="Standard adult meal equivalent (~1.2 kg net surplus food per meal).",
    )
    co2e_factor = ImpactFactorDetail(
        factor_name="impact_co2e_factor",
        value=settings.impact_co2e_factor,
        unit="kg CO2e / kg",
        source="EPA Waste Reduction Model (WARM) v15 / UNEP Food Waste Index Report 2021",
        status="unverified_estimate",
        description="Modeled lifecycle greenhouse gas emissions avoided by diverting organic waste from landfill.",
    )
    return ImpactMethodologyRead(
        version="v1.0",
        meal_kg_factor=meal_factor,
        co2e_factor=co2e_factor,
        disclaimer=CO2E_DISCLAIMER,
    )


def meals_equivalent(weight_kg: float, factor: float | None = None) -> float:
    """Calculate meal equivalents from rescued food weight.

    Methodology:
    Conversion factor is configurable via MEAL_KG_FACTOR (default 1.2 kg/meal).
    Reference: USDA Food Loss and Waste metrics / ReFED surplus food redistribution guidelines.
    """
    if factor is None:
        factor = get_settings().meal_kg_factor
    if factor <= 0:
        raise ValueError("Meal conversion factor must be strictly positive.")
    return round(float(weight_kg) / factor, 1)


def co2e_avoided(weight_kg: float, factor: float | None = None) -> float:
    """Calculate greenhouse gas emissions avoided in kg CO2e.

    Methodology:
    Conversion factor is configurable via IMPACT_CO2E_FACTOR (default 2.5 kg CO2e/kg).
    Citation: Derived from EPA WARM (Waste Reduction Model) and UNEP Food Waste Index reports.
    Status: UNVERIFIED estimate (peer-reviewed verification pending in pilot operations).
    """
    if factor is None:
        factor = get_settings().impact_co2e_factor
    if factor < 0:
        raise ValueError("CO2e factor cannot be negative.")
    return round(float(weight_kg) * factor, 2)


def compute_donation_impact(
    weight_kg: float,
    meal_factor: float | None = None,
    co2e_factor: float | None = None,
) -> dict[str, Any]:
    """Compute complete impact payload for a given weight in kg."""
    meals = meals_equivalent(weight_kg, factor=meal_factor)
    co2e = co2e_avoided(weight_kg, factor=co2e_factor)
    return {
        "kg_rescued": round(float(weight_kg), 2),
        "meals_equivalent": meals,
        "co2e_avoided_kg": co2e,
        "method_version": IMPACT_METHOD_VERSION,
        "co2e_is_estimate": True,
        "disclaimer": CO2E_DISCLAIMER,
    }


async def get_impact_summary(
    db: AsyncSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    donor_id: uuid.UUID | None = None,
    recipient_id: uuid.UUID | None = None,
) -> ImpactSummaryRead:
    """Aggregate total rescued weight, meal equivalents, and estimated avoided emissions."""
    query = (
        select(
            func.count(ImpactLog.id),
            func.coalesce(func.sum(ImpactLog.kg_rescued), 0.0),
            func.coalesce(func.sum(ImpactLog.meals_equivalent), 0.0),
            func.coalesce(func.sum(ImpactLog.co2e_avoided_kg), 0.0),
        )
        .select_from(ImpactLog)
        .join(Donation, ImpactLog.donation_id == Donation.id)
    )

    if recipient_id is not None:
        query = query.join(
            Claim,
            (Claim.donation_id == Donation.id) & (Claim.status == ClaimStatus.picked_up),
        ).where(Claim.recipient_id == recipient_id)

    if donor_id is not None:
        query = query.where(Donation.donor_id == donor_id)

    if start_date is not None:
        query = query.where(ImpactLog.computed_at >= start_date)

    if end_date is not None:
        query = query.where(ImpactLog.computed_at <= end_date)

    res = await db.execute(query)
    total_count, total_kg, total_meals, total_co2e = res.one()

    settings = get_settings()
    return ImpactSummaryRead(
        total_donations_rescued=int(total_count),
        total_kg_rescued=round(float(total_kg), 2),
        total_meals_equivalent=round(float(total_meals), 1),
        total_co2e_avoided_kg=round(float(total_co2e), 2),
        co2e_is_estimate=True,
        method_version=IMPACT_METHOD_VERSION,
        disclaimer=CO2E_DISCLAIMER,
        factors={
            "meal_kg_factor": settings.meal_kg_factor,
            "impact_co2e_factor": settings.impact_co2e_factor,
            "co2e_status": "unverified_estimate",
        },
    )


async def get_impact_timeseries(
    db: AsyncSession,
    interval: str = "day",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    donor_id: uuid.UUID | None = None,
    recipient_id: uuid.UUID | None = None,
) -> ImpactTimeseriesRead:
    """Aggregate historical impact metrics grouped by interval (day, week, month)."""
    valid_intervals = {"day": "day", "week": "week", "month": "month"}
    pg_interval = valid_intervals.get(interval.lower(), "day")

    date_trunc_expr = func.date_trunc(pg_interval, ImpactLog.computed_at)

    query = (
        select(
            date_trunc_expr.label("period_bucket"),
            func.count(ImpactLog.id),
            func.coalesce(func.sum(ImpactLog.kg_rescued), 0.0),
            func.coalesce(func.sum(ImpactLog.meals_equivalent), 0.0),
            func.coalesce(func.sum(ImpactLog.co2e_avoided_kg), 0.0),
        )
        .select_from(ImpactLog)
        .join(Donation, ImpactLog.donation_id == Donation.id)
    )

    if recipient_id is not None:
        query = query.join(
            Claim,
            (Claim.donation_id == Donation.id) & (Claim.status == ClaimStatus.picked_up),
        ).where(Claim.recipient_id == recipient_id)

    if donor_id is not None:
        query = query.where(Donation.donor_id == donor_id)

    if start_date is not None:
        query = query.where(ImpactLog.computed_at >= start_date)

    if end_date is not None:
        query = query.where(ImpactLog.computed_at <= end_date)

    query = query.group_by(date_trunc_expr).order_by(date_trunc_expr.asc())

    res = await db.execute(query)
    rows = res.all()

    points: list[ImpactTimeseriesPoint] = []
    for bucket, count, kg, meals, co2e in rows:
        if isinstance(bucket, datetime):
            period_str = bucket.strftime("%Y-%m-%d")
        else:
            period_str = str(bucket)[:10]

        points.append(
            ImpactTimeseriesPoint(
                period=period_str,
                donations_count=int(count),
                kg_rescued=round(float(kg), 2),
                meals_equivalent=round(float(meals), 1),
                co2e_avoided_kg=round(float(co2e), 2),
                co2e_is_estimate=True,
            )
        )

    summary = await get_impact_summary(
        db=db,
        start_date=start_date,
        end_date=end_date,
        donor_id=donor_id,
        recipient_id=recipient_id,
    )

    return ImpactTimeseriesRead(
        interval=interval,
        points=points,
        summary=summary,
    )


async def generate_impact_csv(
    db: AsyncSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    donor_id: uuid.UUID | None = None,
    recipient_id: uuid.UUID | None = None,
) -> str:
    """Generate auditable CSV export containing all historical impact records."""
    query = (
        select(ImpactLog)
        .options(
            selectinload(ImpactLog.donation).selectinload(Donation.donor).selectinload(Donor.user),
            selectinload(ImpactLog.donation)
            .selectinload(Donation.claims)
            .selectinload(Claim.recipient)
            .selectinload(Recipient.user),
        )
        .join(Donation, ImpactLog.donation_id == Donation.id)
    )

    if recipient_id is not None:
        query = query.join(
            Claim,
            (Claim.donation_id == Donation.id) & (Claim.status == ClaimStatus.picked_up),
        ).where(Claim.recipient_id == recipient_id)

    if donor_id is not None:
        query = query.where(Donation.donor_id == donor_id)

    if start_date is not None:
        query = query.where(ImpactLog.computed_at >= start_date)

    if end_date is not None:
        query = query.where(ImpactLog.computed_at <= end_date)

    query = query.order_by(ImpactLog.computed_at.desc())

    res = await db.execute(query)
    logs = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # CSV Header
    writer.writerow(
        [
            "impact_id",
            "donation_id",
            "computed_at",
            "donor_id",
            "donor_name",
            "recipient_id",
            "recipient_name",
            "item",
            "category",
            "kg_rescued",
            "meals_equivalent",
            "co2e_avoided_kg",
            "method_version",
            "co2e_is_estimate",
        ]
    )

    for log in logs:
        donation = log.donation
        donor = donation.donor if donation else None
        donor_name = (
            donor.user.display_name or donor.user.org_name
            if donor and donor.user
            else "Unknown Donor"
        )
        picked_up_claim = None
        if donation and donation.claims:
            picked_up_claim = next(
                (c for c in donation.claims if c.status == ClaimStatus.picked_up), None
            )

        recipient_id_str = str(picked_up_claim.recipient_id) if picked_up_claim else ""
        recipient_name = "Unknown Recipient"
        if picked_up_claim and picked_up_claim.recipient and picked_up_claim.recipient.user:
            recipient_name = (
                picked_up_claim.recipient.user.org_name
                or picked_up_claim.recipient.user.display_name
                or "Recipient Partner"
            )

        writer.writerow(
            [
                str(log.id),
                str(log.donation_id),
                log.computed_at.isoformat() if log.computed_at else "",
                str(donation.donor_id) if donation else "",
                donor_name,
                recipient_id_str,
                recipient_name,
                donation.item.value if donation else "food",
                donation.category
                if hasattr(donation, "category") and donation.category
                else "general",
                f"{float(log.kg_rescued):.2f}",
                f"{float(log.meals_equivalent):.1f}",
                f"{float(log.co2e_avoided_kg):.2f}",
                log.method_version or IMPACT_METHOD_VERSION,
                "true",
            ]
        )

    return output.getvalue()


async def reconcile_impact(db: AsyncSession) -> ImpactReconciliationRead:
    """Audit SQL reconciliation across completed claims, donations, and impact_log records.

    Verifies the invariant:
    COUNT(picked_up claims) == COUNT(completed donations) == COUNT(impact_log rows)
    SUM(donation.est_weight_kg) == SUM(impact_log.kg_rescued)
    """
    # 1. Count completed claims
    claims_count = (
        await db.execute(select(func.count(Claim.id)).where(Claim.status == ClaimStatus.picked_up))
    ).scalar_one() or 0

    # 2. Count completed donations and sum weight
    d_res = await db.execute(
        select(
            func.count(Donation.id),
            func.coalesce(func.sum(Donation.est_weight_kg), 0.0),
        ).where(Donation.status == DonationStatus.completed)
    )
    donations_count, total_d_weight = d_res.one()

    # 3. Count impact rows and sum rescued weight
    i_res = await db.execute(
        select(
            func.count(ImpactLog.id),
            func.coalesce(func.sum(ImpactLog.kg_rescued), 0.0),
        )
    )
    impact_count, total_i_weight = i_res.one()

    weight_delta = round(abs(float(total_d_weight) - float(total_i_weight)), 2)
    discrepancies: list[str] = []

    if claims_count != donations_count:
        discrepancies.append(
            f"Claims count ({claims_count}) does not match completed donations count ({donations_count})"
        )

    if donations_count != impact_count:
        discrepancies.append(
            f"Completed donations count ({donations_count}) does not match impact rows count ({impact_count})"
        )

    if weight_delta > 0.01:
        discrepancies.append(
            f"Weight mismatch: completed donations total {total_d_weight:.2f}kg vs impact records total {total_i_weight:.2f}kg (delta: {weight_delta:.2f}kg)"
        )

    # Check for completed donations missing an impact log
    missing_stmt = (
        select(Donation.id)
        .outerjoin(ImpactLog, Donation.id == ImpactLog.donation_id)
        .where(
            Donation.status == DonationStatus.completed,
            ImpactLog.id.is_(None),
        )
    )
    missing_ids = (await db.execute(missing_stmt)).scalars().all()
    for m_id in missing_ids:
        discrepancies.append(f"Completed donation {m_id} has no corresponding ImpactLog row")

    reconciled = len(discrepancies) == 0

    return ImpactReconciliationRead(
        reconciled=reconciled,
        completed_claims_count=int(claims_count),
        completed_donations_count=int(donations_count),
        impact_rows_count=int(impact_count),
        total_donation_weight_kg=round(float(total_d_weight), 2),
        total_impact_kg_rescued=round(float(total_i_weight), 2),
        weight_delta_kg=weight_delta,
        discrepancies=discrepancies,
    )
