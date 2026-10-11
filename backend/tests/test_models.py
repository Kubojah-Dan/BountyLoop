"""BountyLoop — Model Unit Tests (Phase 1).

Tests entity instantiation, database persistence, relationships,
and lifecycle fields for all core models.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentEvent,
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
    ReviewQueue,
    ReviewReason,
    ReviewStatus,
    User,
    UserRole,
)


@pytest.mark.anyio
async def test_user_creation_and_query(db_session: AsyncSession) -> None:
    """Test user creation with various roles and query persistence."""
    uid = f"test_fb_{uuid.uuid4().hex[:8]}"
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        firebase_uid=uid,
        role=UserRole.donor,
        display_name="Test Donor User",
        email=email,
        phone_e164="+15125559999",
        org_name="Test Bakery",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.email == email))
    saved_user = result.scalar_one()
    assert saved_user.id == user.id
    assert saved_user.firebase_uid == uid
    assert saved_user.role == UserRole.donor
    assert saved_user.is_active is True
    assert saved_user.created_at is not None


@pytest.mark.anyio
async def test_donor_and_recipient_creation(db_session: AsyncSession) -> None:
    """Test donor and recipient creation with PostGIS Geography coordinates."""
    # Create Donor User
    d_user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_d_{uuid.uuid4().hex[:8]}",
        role=UserRole.donor,
        display_name="Austin Urban Market",
        email=f"donor_{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(d_user)
    await db_session.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=d_user.id,
        kind=DonorKind.grocery,
        address="100 Congress Ave, Austin, TX 78701",
        location=WKTElement("POINT(-97.7431 30.2642)", srid=4326),
        timezone="America/Chicago",
        avg_surplus_schedule={"daily_surplus_time": "19:00"},
    )
    db_session.add(donor)

    # Create Recipient User
    r_user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_r_{uuid.uuid4().hex[:8]}",
        role=UserRole.recipient,
        display_name="Community Kitchen Austin",
        email=f"recip_{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(r_user)
    await db_session.flush()

    recipient = Recipient(
        id=uuid.uuid4(),
        user_id=r_user.id,
        org_type=RecipientOrgType.shelter,
        address="500 E 7th St, Austin, TX 78701",
        location=WKTElement("POINT(-97.7370 30.2675)", srid=4326),
        capacity_kg_per_day=300.0,
        accepted_items=["prepared_cooked", "bread_bakery", "dairy"],
        cold_chain=True,
        urgency_weight=1.3,
        is_accepting=True,
    )
    db_session.add(recipient)
    await db_session.commit()

    # Query back
    saved_donor = (await db_session.execute(select(Donor).where(Donor.id == donor.id))).scalar_one()
    assert saved_donor.kind == DonorKind.grocery
    assert saved_donor.timezone == "America/Chicago"

    saved_recip = (
        await db_session.execute(select(Recipient).where(Recipient.id == recipient.id))
    ).scalar_one()
    assert saved_recip.capacity_kg_per_day == 300.0
    assert saved_recip.cold_chain is True
    assert "bread_bakery" in saved_recip.accepted_items


@pytest.mark.anyio
async def test_donation_and_claim_lifecycle(db_session: AsyncSession) -> None:
    """Test donation creation, claims, impact log, and review queue."""
    now = datetime.now(UTC)

    # Setup donor & recipient
    u1 = User(
        id=uuid.uuid4(),
        firebase_uid=f"u1_{uuid.uuid4().hex[:6]}",
        role=UserRole.donor,
        display_name="Baker",
        email=f"baker_{uuid.uuid4().hex[:6]}@test.com",
    )
    u2 = User(
        id=uuid.uuid4(),
        firebase_uid=f"u2_{uuid.uuid4().hex[:6]}",
        role=UserRole.recipient,
        display_name="Pantry",
        email=f"pantry_{uuid.uuid4().hex[:6]}@test.com",
    )
    db_session.add_all([u1, u2])
    await db_session.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=u1.id,
        kind=DonorKind.restaurant,
        address="200 E 6th St, Austin, TX",
        location=WKTElement("POINT(-97.7410 30.2670)", srid=4326),
    )
    recipient = Recipient(
        id=uuid.uuid4(),
        user_id=u2.id,
        org_type=RecipientOrgType.food_bank,
        address="800 E 12th St, Austin, TX",
        location=WKTElement("POINT(-97.7290 30.2740)", srid=4326),
        capacity_kg_per_day=500.0,
        accepted_items=["produce_fruit"],
    )
    db_session.add_all([donor, recipient])
    await db_session.flush()

    # Create Donation
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor.id,
        photo_paths=["storage/photos/test_fruit.jpg"],
        item=FoodCategory.produce_fruit,
        item_confidence=0.9520,
        freshness=FreshnessGrade.fresh,
        freshness_confidence=0.9230,
        hazard_flag=HazardFlag.none,
        est_weight_kg=42.5,
        expires_at=now + timedelta(hours=48),
        status=DonationStatus.open,
        needs_review=False,
    )
    db_session.add(donation)
    await db_session.flush()

    # Create Claim
    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.offered,
        score=0.9300,
        score_breakdown={"distance_km": 1.5, "fit": 0.95},
    )
    db_session.add(claim)

    # Create ReviewQueue item
    review = ReviewQueue(
        id=uuid.uuid4(),
        donation_id=donation.id,
        reason=ReviewReason.low_confidence,
        status=ReviewStatus.pending,
        note="Model confidence borderline for secondary head",
    )
    db_session.add(review)

    # Create AgentEvent
    event = AgentEvent(
        id=uuid.uuid4(),
        donation_id=donation.id,
        event_type="DISPATCH_DECISION",
        payload={"action": "offer_sent", "candidate_count": 3},
        model="bountyloop-agent-v1",
        latency_ms=185,
    )
    db_session.add(event)

    # Create ImpactLog
    impact = ImpactLog(
        id=uuid.uuid4(),
        donation_id=donation.id,
        kg_rescued=42.5,
        meals_equivalent=51.0,
        co2e_avoided_kg=106.25,
        method_version="v1.0",
    )
    db_session.add(impact)

    await db_session.commit()

    # Verify query
    saved_d = (
        await db_session.execute(select(Donation).where(Donation.id == donation.id))
    ).scalar_one()
    assert saved_d.est_weight_kg == 42.5
    assert saved_d.item == FoodCategory.produce_fruit
    assert saved_d.freshness == FreshnessGrade.fresh

    saved_claim = (await db_session.execute(select(Claim).where(Claim.id == claim.id))).scalar_one()
    assert saved_claim.score == 0.9300

    saved_impact = (
        await db_session.execute(select(ImpactLog).where(ImpactLog.donation_id == donation.id))
    ).scalar_one()
    assert saved_impact.kg_rescued == 42.5
    assert saved_impact.meals_equivalent == 51.0
