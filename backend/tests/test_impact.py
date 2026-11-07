"""BountyLoop — Comprehensive Tests for Impact Measurement & Methodology (§Master Plan §6 Phase 10).

Covers:
1. Pure calculations: meals_equivalent (1.2 kg/meal factor), co2e_avoided (2.5 kg/kg UNVERIFIED factor),
   compute_donation_impact payload, invalid non-positive factors.
2. Methodology transparency endpoint (GET /v1/impact/methodology).
3. Single-row idempotency contract: completing a pickup twice writes exactly ONE ImpactLog row.
4. Summary metrics endpoint (GET /v1/impact/summary) with date & donor filters.
5. Timeseries aggregation endpoint (GET /v1/impact/timeseries).
6. Granular CSV data export (GET /v1/impact/export/csv).
7. SQL reconciliation audit endpoint (GET /v1/impact/reconciliation).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from geoalchemy2.elements import WKTElement
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Claim,
    ClaimStatus,
    Donation,
    DonationStatus,
    Donor,
    DonorKind,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    ImpactLog,
    Recipient,
    RecipientOrgType,
    User,
    UserRole,
)
from app.services.impact import (
    co2e_avoided,
    compute_donation_impact,
    meals_equivalent,
)

MOCK_RECIPIENT_USER = {
    "uid": "fb_recip_impact_test_01",
    "email": "recipient_impact@bountyloop.org",
    "name": "Austin Community Food Bank",
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pure Calculation & Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_meals_equivalent_default_factor() -> None:
    """12 kg rescued at 1.2 kg/meal yields exactly 10.0 meals."""
    assert meals_equivalent(12.0) == 10.0
    assert meals_equivalent(6.0) == 5.0
    assert meals_equivalent(1.8) == 1.5
    assert meals_equivalent(0.0) == 0.0


def test_co2e_avoided_default_factor() -> None:
    """10 kg rescued at 2.5 kg CO2e/kg yields 25.0 kg CO2e avoided."""
    assert co2e_avoided(10.0) == 25.0
    assert co2e_avoided(4.2) == 10.50
    assert co2e_avoided(0.0) == 0.0


def test_compute_donation_impact_payload() -> None:
    """compute_donation_impact outputs complete structured impact dictionary."""
    impact = compute_donation_impact(15.0)
    assert impact["kg_rescued"] == 15.0
    assert impact["meals_equivalent"] == 12.5
    assert impact["co2e_avoided_kg"] == 37.5
    assert impact["method_version"] == "v1"
    assert impact["co2e_is_estimate"] is True
    assert "landfill diversion" in impact["disclaimer"].lower()


def test_invalid_factors_raise_error() -> None:
    """Non-positive meal factor or negative CO2e factor raises ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        meals_equivalent(10.0, factor=0.0)

    with pytest.raises(ValueError, match="strictly positive"):
        meals_equivalent(10.0, factor=-1.2)

    with pytest.raises(ValueError, match="cannot be negative"):
        co2e_avoided(10.0, factor=-1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Methodology & Metadata Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_methodology_endpoint(client: AsyncClient) -> None:
    """GET /v1/impact/methodology returns full transparency metadata and factor citations."""
    resp = await client.get("/v1/impact/methodology")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "v1.0"
    assert data["meal_kg_factor"]["value"] == 1.2
    assert "USDA" in data["meal_kg_factor"]["source"]
    assert data["co2e_factor"]["value"] == 2.5
    assert data["co2e_factor"]["status"] == "unverified_estimate"
    assert "WARM" in data["co2e_factor"]["source"]
    assert "not laboratory-measured" in data["disclaimer"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Helpers for Database Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


async def _create_impact_test_donor(
    db: AsyncSession,
    name: str = "Austin Harvest Market",
) -> tuple[User, Donor]:
    """Helper to persist a test donor."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_donor_{uuid.uuid4().hex[:8]}",
        email=f"donor_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.donor,
        display_name=name,
        org_name=name,
        phone_e164="+15125550701",
    )
    db.add(user)
    await db.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.grocery,
        address="500 Congress Ave, Austin, TX",
        location=WKTElement("POINT(-97.7431 30.2672)", srid=4326),
    )
    db.add(donor)
    await db.commit()
    await db.refresh(user)
    await db.refresh(donor)
    return user, donor


async def _create_impact_test_recipient(
    db: AsyncSession,
    name: str = "Central Texas Food Bank",
) -> tuple[User, Recipient]:
    """Helper to persist a test recipient organization."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_recip_{uuid.uuid4().hex[:8]}",
        email=f"recip_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.recipient,
        display_name=name,
        org_name=name,
        phone_e164="+15125550702",
    )
    db.add(user)
    await db.flush()

    recipient = Recipient(
        id=uuid.uuid4(),
        user_id=user.id,
        org_type=RecipientOrgType.food_bank,
        address="6500 Metropolis Dr, Austin, TX",
        location=WKTElement("POINT(-97.7121 30.2185)", srid=4326),
        capacity_kg_per_day=1000.0,
        accepted_items=["produce_fruit", "bread_bakery"],
        is_accepting=True,
    )
    db.add(recipient)
    await db.commit()
    await db.refresh(user)
    await db.refresh(recipient)
    return user, recipient


async def _create_impact_test_donation_and_claim(
    db: AsyncSession,
    donor: Donor,
    recipient: Recipient,
    weight_kg: float = 24.0,
    status: ClaimStatus = ClaimStatus.offered,
) -> tuple[Donation, Claim]:
    """Helper to persist a test donation with associated claim."""
    now = datetime.now(UTC)
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor.id,
        item=FoodCategory.bread_bakery,
        item_confidence=0.95,
        freshness=FreshnessGrade.fresh,
        freshness_confidence=0.92,
        hazard_flag=HazardFlag.none,
        est_weight_kg=weight_kg,
        expires_at=now + timedelta(hours=24),
        status=DonationStatus.matched if status != ClaimStatus.offered else DonationStatus.open,
        needs_review=False,
    )
    db.add(donation)
    await db.flush()

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=status,
        score=90.0,
        offered_at=now,
        responded_at=now if status != ClaimStatus.offered else None,
        picked_up_at=now if status == ClaimStatus.picked_up else None,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(donation)
    await db.refresh(claim)
    return donation, claim


# ─────────────────────────────────────────────────────────────────────────────
# 4. Single-Row Idempotency & Pickup Verification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_single_row_idempotency_on_pickup(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verifies that confirming pickup multiple times produces exactly ONE ImpactLog row."""
    _, donor = await _create_impact_test_donor(db_session, name="Idempotency Bakery")
    _, recipient = await _create_impact_test_recipient(db_session, name="Idempotency Pantry")
    donation, claim = await _create_impact_test_donation_and_claim(
        db_session, donor, recipient, weight_kg=12.0, status=ClaimStatus.accepted
    )

    with patch("app.core.security.verify_firebase_token", return_value=MOCK_RECIPIENT_USER):
        headers = {"Authorization": "Bearer test_token"}

        # First pickup confirmation
        resp1 = await client.post(
            f"/v1/claims/{claim.id}/pickup",
            headers=headers,
            json={"proof_photo_path": "/storage/proof_1.jpg"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["status"] == "picked_up"
        assert data1["impact"] is not None
        assert data1["impact"]["kg_rescued"] == 12.0
        assert data1["impact"]["meals_equivalent"] == 10.0
        assert data1["impact"]["co2e_avoided_kg"] == 30.0

        # Second pickup confirmation (simulated retry / network replay)
        resp2 = await client.post(
            f"/v1/claims/{claim.id}/pickup",
            headers=headers,
            json={"proof_photo_path": "/storage/proof_1.jpg"},
        )
        assert resp2.status_code == 200

        # Verify DB: exactly ONE ImpactLog row exists for this donation
        stmt = select(ImpactLog).where(ImpactLog.donation_id == donation.id)
        rows = (await db_session.execute(stmt)).scalars().all()
        assert len(rows) == 1
        assert float(rows[0].kg_rescued) == 12.0
        assert float(rows[0].meals_equivalent) == 10.0
        assert float(rows[0].co2e_avoided_kg) == 30.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Summary Endpoint & Filters
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_summary_endpoint_and_filters(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /v1/impact/summary aggregates totals and supports donor_id filtering."""
    _, donor_a = await _create_impact_test_donor(db_session, name="Donor Alpha")
    _, donor_b = await _create_impact_test_donor(db_session, name="Donor Beta")
    _, recipient = await _create_impact_test_recipient(db_session, name="Summary Shelter")

    # Add 2 completed donations for donor A (10kg + 20kg = 30kg)
    d1, _ = await _create_impact_test_donation_and_claim(
        db_session, donor_a, recipient, weight_kg=10.0, status=ClaimStatus.picked_up
    )
    d1.status = DonationStatus.completed
    i1 = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d1.id,
        kg_rescued=10.0,
        meals_equivalent=8.3,
        co2e_avoided_kg=25.0,
        method_version="v1.0",
    )
    db_session.add(i1)

    d2, _ = await _create_impact_test_donation_and_claim(
        db_session, donor_a, recipient, weight_kg=20.0, status=ClaimStatus.picked_up
    )
    d2.status = DonationStatus.completed
    i2 = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d2.id,
        kg_rescued=20.0,
        meals_equivalent=16.7,
        co2e_avoided_kg=50.0,
        method_version="v1.0",
    )
    db_session.add(i2)

    # Add 1 completed donation for donor B (15kg)
    d3, _ = await _create_impact_test_donation_and_claim(
        db_session, donor_b, recipient, weight_kg=15.0, status=ClaimStatus.picked_up
    )
    d3.status = DonationStatus.completed
    i3 = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d3.id,
        kg_rescued=15.0,
        meals_equivalent=12.5,
        co2e_avoided_kg=37.5,
        method_version="v1.0",
    )
    db_session.add(i3)
    await db_session.commit()

    # 1. Global summary
    resp_all = await client.get("/v1/impact/summary")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["total_donations_rescued"] >= 3
    assert data_all["total_kg_rescued"] >= 45.0
    assert data_all["co2e_is_estimate"] is True
    assert "unverified" in data_all["factors"]["co2e_status"]

    # 2. Filtered summary for donor A only
    resp_a = await client.get(f"/v1/impact/summary?donor_id={donor_a.id}")
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total_donations_rescued"] == 2
    assert data_a["total_kg_rescued"] == 30.0
    assert data_a["total_meals_equivalent"] == 25.0
    assert data_a["total_co2e_avoided_kg"] == 75.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Timeseries Aggregation Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_timeseries_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /v1/impact/timeseries aggregates metrics by interval (day, week)."""
    _, donor = await _create_impact_test_donor(db_session, name="Timeseries Bakery")
    _, recipient = await _create_impact_test_recipient(db_session, name="Timeseries Pantry")

    d, _ = await _create_impact_test_donation_and_claim(
        db_session, donor, recipient, weight_kg=18.0, status=ClaimStatus.picked_up
    )
    d.status = DonationStatus.completed
    i = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d.id,
        kg_rescued=18.0,
        meals_equivalent=15.0,
        co2e_avoided_kg=45.0,
        method_version="v1.0",
    )
    db_session.add(i)
    await db_session.commit()

    # Query daily interval
    resp = await client.get("/v1/impact/timeseries?interval=day")
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval"] == "day"
    assert len(data["points"]) >= 1
    assert data["points"][0]["kg_rescued"] >= 18.0
    assert data["points"][0]["co2e_is_estimate"] is True
    assert data["summary"]["total_kg_rescued"] >= 18.0

    # Query weekly interval
    resp_week = await client.get("/v1/impact/timeseries?interval=week")
    assert resp_week.status_code == 200
    data_week = resp_week.json()
    assert data_week["interval"] == "week"
    assert len(data_week["points"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 7. CSV Export Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_csv_export_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /v1/impact/export/csv generates valid downloadable CSV with standard columns."""
    _, donor = await _create_impact_test_donor(db_session, name="CSV Export Donor")
    _, recipient = await _create_impact_test_recipient(db_session, name="CSV Export Shelter")

    d, _ = await _create_impact_test_donation_and_claim(
        db_session, donor, recipient, weight_kg=22.0, status=ClaimStatus.picked_up
    )
    d.status = DonationStatus.completed
    i = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d.id,
        kg_rescued=22.0,
        meals_equivalent=18.3,
        co2e_avoided_kg=55.0,
        method_version="v1.0",
    )
    db_session.add(i)
    await db_session.commit()

    resp = await client.get(f"/v1/impact/export/csv?donor_id={donor.id}")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]

    # Parse CSV content
    csv_text = resp.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + at least 1 record

    header = rows[0]
    expected_columns = [
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
    for col in expected_columns:
        assert col in header

    # Verify data row
    data_row = rows[1]
    assert data_row[header.index("donor_name")] == "CSV Export Donor"
    assert data_row[header.index("kg_rescued")] == "22.00"
    assert data_row[header.index("co2e_avoided_kg")] == "55.00"
    assert data_row[header.index("co2e_is_estimate")] == "true"


# ─────────────────────────────────────────────────────────────────────────────
# 8. SQL Reconciliation Audit Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_impact_reconciliation_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /v1/impact/reconciliation verifies 1:1 match across claims, donations, and impact logs."""
    # 1. Balanced state test
    _, donor = await _create_impact_test_donor(db_session, name="Reconcile Farm")
    _, recipient = await _create_impact_test_recipient(db_session, name="Reconcile Pantry")

    d, _ = await _create_impact_test_donation_and_claim(
        db_session, donor, recipient, weight_kg=30.0, status=ClaimStatus.picked_up
    )
    d.status = DonationStatus.completed
    i = ImpactLog(
        id=uuid.uuid4(),
        donation_id=d.id,
        kg_rescued=30.0,
        meals_equivalent=25.0,
        co2e_avoided_kg=75.0,
        method_version="v1.0",
    )
    db_session.add(i)
    await db_session.commit()

    resp = await client.get("/v1/impact/reconciliation")
    assert resp.status_code == 200
    data = resp.json()
    assert "reconciled" in data
    assert "completed_claims_count" in data
    assert "impact_rows_count" in data
    assert "weight_delta_kg" in data
    assert data["weight_delta_kg"] >= 0.0

    # 2. Test discrepancy detection: create an unlogged completed donation
    d_orphan = Donation(
        id=uuid.uuid4(),
        donor_id=donor.id,
        item=FoodCategory.produce_fruit,
        item_confidence=0.90,
        freshness=FreshnessGrade.fresh,
        freshness_confidence=0.90,
        hazard_flag=HazardFlag.none,
        est_weight_kg=15.0,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
        status=DonationStatus.completed,  # Completed but missing ImpactLog
        needs_review=False,
    )
    db_session.add(d_orphan)
    await db_session.commit()

    resp_discrepancy = await client.get("/v1/impact/reconciliation")
    assert resp_discrepancy.status_code == 200
    disc_data = resp_discrepancy.json()
    assert disc_data["reconciled"] is False
    assert any(str(d_orphan.id) in d for d in disc_data["discrepancies"])
