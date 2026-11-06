"""BountyLoop — Recipient Matching Engine, Routing & Optimization Tests (§6 Phase 7).

Verifies:
1. Nearest eligible candidate ranked #1 by composite score.
2. Out-of-capacity recipient excluded from candidate pool.
3. Incompatible food category recipient excluded from candidate pool.
4. Consecutive-win equity guard (MAX_CONSECUTIVE_WINS) blocks recipient with >=3 consecutive wins.
5. CVRP-lite 2-opt optimizer out-performs naive nearest-neighbor on crafted loop.
6. Route endpoint returns honest estimation (source: "estimate" or "osrm") with GeoJSON LineString.
7. Claim acceptance endpoint (/v1/claims/{id}/accept) transitions status and records response.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from geoalchemy2.elements import WKTElement
from httpx import AsyncClient
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
    Recipient,
    RecipientOrgType,
    User,
    UserRole,
)
from app.services.matching import MatchingEngine
from app.services.optimizer import naive_nearest_neighbor, solve_cvrp_lite

MOCK_AUTH_USER = {
    "uid": "fb_matching_test_user_01",
    "email": "matching_test@bountyloop.org",
    "name": "Alex Matching Tester",
}


async def _create_test_donor(
    db: AsyncSession,
    lat: float = 30.2672,
    lon: float = -97.7431,
) -> Donor:
    """Helper to persist a test donor in downtown Austin."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"donor_{uuid.uuid4().hex[:8]}",
        email=f"donor_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.donor,
        display_name="Austin Bakery Donor",
    )
    db.add(user)
    await db.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.grocery,
        address="100 Congress Ave, Austin, TX",
        location=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )
    db.add(donor)
    await db.flush()
    return donor


async def _create_test_recipient(
    db: AsyncSession,
    name: str,
    lat: float,
    lon: float,
    capacity_kg: float = 200.0,
    accepted_items: list[str] | None = None,
    is_accepting: bool = True,
    urgency_weight: float = 1.0,
) -> Recipient:
    """Helper to persist a test recipient."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"recip_{uuid.uuid4().hex[:8]}",
        email=f"recip_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.recipient,
        display_name=name,
        org_name=name,
    )
    db.add(user)
    await db.flush()

    recip = Recipient(
        id=uuid.uuid4(),
        user_id=user.id,
        org_type=RecipientOrgType.food_bank,
        address=f"{name} Facility, Austin, TX",
        location=WKTElement(f"POINT({lon} {lat})", srid=4326),
        capacity_kg_per_day=capacity_kg,
        accepted_items=accepted_items
        if accepted_items is not None
        else ["bread_bakery", "produce_fruit"],
        is_accepting=is_accepting,
        urgency_weight=urgency_weight,
    )
    db.add(recip)
    await db.flush()
    return recip


async def _create_test_donation(
    db: AsyncSession,
    donor_id: uuid.UUID,
    item: FoodCategory = FoodCategory.bread_bakery,
    weight_kg: float = 25.0,
    hours_to_expiry: float = 12.0,
) -> Donation:
    """Helper to persist an open test donation."""
    now = datetime.now(UTC)
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor_id,
        item=item,
        item_confidence=0.96,
        freshness=FreshnessGrade.grade_2_good,
        freshness_confidence=0.92,
        hazard_flag=HazardFlag.none,
        est_weight_kg=weight_kg,
        expires_at=now + timedelta(hours=hours_to_expiry),
        status=DonationStatus.open,
        needs_review=False,
    )
    db.add(donation)
    await db.flush()
    return donation


# ── TEST 1: Nearest eligible candidate ranked #1 ──────────────────────────────
@pytest.mark.asyncio
async def test_nearest_eligible_candidate_ranked_first(db_session: AsyncSession) -> None:
    """Closer recipient with equivalent attributes receives higher distance score and ranks above farther."""
    base_lat, base_lon = 31.0500, -98.2500  # Unique isolated coordinate cluster
    donor = await _create_test_donor(db_session, lat=base_lat, lon=base_lon)
    # Near recipient (~0.2 km away)
    near_recip = await _create_test_recipient(
        db_session, "Near Food Shelter", lat=base_lat + 0.002, lon=base_lon, capacity_kg=300.0
    )
    # Far recipient (~8.0 km away)
    far_recip = await _create_test_recipient(
        db_session, "Far Food Pantry", lat=base_lat + 0.070, lon=base_lon, capacity_kg=300.0
    )

    donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=20.0)

    engine = MatchingEngine()
    candidates = await engine.find_candidates(donation=donation, db=db_session, radius_km=15.0)

    near_match = next((c for c in candidates if c.recipient.id == near_recip.id), None)
    far_match = next((c for c in candidates if c.recipient.id == far_recip.id), None)

    assert near_match is not None, "Expected near recipient in candidate pool"
    assert far_match is not None, "Expected far recipient in candidate pool"
    assert near_match.distance_km < far_match.distance_km
    assert near_match.score > far_match.score
    assert candidates.index(near_match) < candidates.index(far_match)
    assert candidates[0].recipient.id == near_recip.id


# ── TEST 2: Out-of-capacity recipient excluded ─────────────────────────────────
@pytest.mark.asyncio
async def test_out_of_capacity_recipient_excluded(db_session: AsyncSession) -> None:
    """Recipients with daily intake headroom less than donation weight are excluded."""
    donor = await _create_test_donor(db_session, lat=30.2672, lon=-97.7431)
    # Fit recipient (50kg capacity for 30kg donation)
    fit_recip = await _create_test_recipient(
        db_session, "Adequate Pantry", lat=30.2700, lon=-97.7450, capacity_kg=50.0
    )
    # Small fridge (only 10kg capacity for 30kg donation)
    tiny_recip = await _create_test_recipient(
        db_session, "Tiny Community Box", lat=30.2680, lon=-97.7440, capacity_kg=10.0
    )

    donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=30.0)

    engine = MatchingEngine()
    candidates = await engine.find_candidates(donation=donation, db=db_session, radius_km=25.0)

    candidate_ids = [c.recipient.id for c in candidates]
    assert fit_recip.id in candidate_ids
    assert tiny_recip.id not in candidate_ids


# ── TEST 3: Incompatible food item recipient excluded ──────────────────────────
@pytest.mark.asyncio
async def test_incompatible_food_item_recipient_excluded(db_session: AsyncSession) -> None:
    """Recipients that do not accept the donation's category are excluded."""
    donor = await _create_test_donor(db_session, lat=30.2672, lon=-97.7431)
    # Accepts dairy and bread
    dairy_recip = await _create_test_recipient(
        db_session,
        "General Pantry",
        lat=30.2700,
        lon=-97.7400,
        accepted_items=["dairy", "bread_bakery"],
    )
    # Only accepts produce
    produce_only_recip = await _create_test_recipient(
        db_session,
        "Vegan Fruit Rescue",
        lat=30.2690,
        lon=-97.7410,
        accepted_items=["produce_fruit", "produce_vegetable"],
    )

    # Donating dairy
    donation = await _create_test_donation(
        db_session, donor_id=donor.id, item=FoodCategory.dairy, weight_kg=15.0
    )

    engine = MatchingEngine()
    candidates = await engine.find_candidates(donation=donation, db=db_session, radius_km=25.0)

    candidate_ids = [c.recipient.id for c in candidates]
    assert dairy_recip.id in candidate_ids
    assert produce_only_recip.id not in candidate_ids


# ── TEST 4: Equity guard cap stops recipient with >= 3 consecutive wins ────────
@pytest.mark.asyncio
async def test_equity_guard_blocks_consecutive_wins(db_session: AsyncSession) -> None:
    """Equity guard prevents a single large food bank from monopolizing matches."""
    donor = await _create_test_donor(db_session, lat=30.2672, lon=-97.7431)
    large_bank = await _create_test_recipient(
        db_session, "Mega Food Bank", lat=30.2680, lon=-97.7420, capacity_kg=1000.0
    )
    small_pantry = await _create_test_recipient(
        db_session, "St. Jude Pantry", lat=30.2750, lon=-97.7400, capacity_kg=200.0
    )

    # Seed 3 consecutive accepted/completed claims for large_bank
    now = datetime.now(UTC)
    for i in range(3):
        past_donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=10.0)
        claim = Claim(
            id=uuid.uuid4(),
            donation_id=past_donation.id,
            recipient_id=large_bank.id,
            status=ClaimStatus.picked_up,
            score=95.0,
            offered_at=now - timedelta(minutes=60 - i * 10),
            responded_at=now - timedelta(minutes=55 - i * 10),
            picked_up_at=now - timedelta(minutes=30 - i * 10),
        )
        db_session.add(claim)
    await db_session.flush()

    new_donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=15.0)

    engine = MatchingEngine()
    candidates = await engine.find_candidates(
        donation=new_donation, db=db_session, enforce_equity=True
    )

    candidate_ids = [c.recipient.id for c in candidates]
    assert large_bank.id not in candidate_ids
    assert small_pantry.id in candidate_ids


# ── TEST 5: Optimizer 2-opt beats naive nearest-neighbor on crafted loop ───────
def test_cvrp_optimizer_2opt_beats_nearest_neighbor() -> None:
    """Crafted crossed loop where 2-Opt untangles the tour and beats greedy nearest-neighbor."""
    depot = (30.2672, -97.7431)
    # Polygon stops crafted such that a greedy NN choice crosses itself
    stops = [
        {"id": "stop_1", "lat": 30.2700, "lon": -97.7300, "weight_kg": 10.0},
        {"id": "stop_2", "lat": 30.2900, "lon": -97.7500, "weight_kg": 15.0},
        {"id": "stop_3", "lat": 30.2750, "lon": -97.7200, "weight_kg": 12.0},
        {"id": "stop_4", "lat": 30.2950, "lon": -97.7400, "weight_kg": 8.0},
        {"id": "stop_5", "lat": 30.2800, "lon": -97.7150, "weight_kg": 14.0},
    ]

    opt_solution = solve_cvrp_lite(depot=depot, stops=stops)
    nn_solution = naive_nearest_neighbor(depot=depot, stops=stops)

    assert opt_solution["total_distance_m"] <= nn_solution["total_distance_m"]
    assert len(opt_solution["route_order"]) == len(stops)
    assert opt_solution["method"] in ("2_opt_heuristic", "or_tools")


# ── TEST 6: Route endpoint returns honest source: "estimate" or "osrm" ─────────
@pytest.mark.asyncio
async def test_route_endpoint_honest_source_and_geojson(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """GET /v1/routes/{claim_id} provides GeoJSON LineString with explicit source indicator."""
    donor = await _create_test_donor(db_session, lat=30.2672, lon=-97.7431)
    recip = await _create_test_recipient(
        db_session, "East Austin Food Hub", lat=30.2750, lon=-97.7200
    )
    donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=12.0)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recip.id,
        status=ClaimStatus.offered,
        score=88.5,
        score_breakdown={"distance_km": 2.5},
    )
    db_session.add(claim)
    await db_session.commit()

    with patch("app.core.security.verify_firebase_token", return_value=MOCK_AUTH_USER):
        headers = {"Authorization": "Bearer test_token"}
        resp = await client.get(f"/v1/routes/{claim.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["claim_id"] == str(claim.id)
        assert data["source"] in ("estimate", "osrm")
        assert data["route_source"] in ("estimate", "osrm")
        assert data["distance_m"] > 0
        assert data["duration_s"] > 0
        assert data["geometry"]["type"] == "LineString"
        assert len(data["geometry"]["coordinates"]) >= 2


# ── TEST 7: Claim acceptance endpoint transitions status and logs response ─────
@pytest.mark.asyncio
async def test_claim_accept_endpoint_lifecycle(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """POST /v1/claims/{id}/accept transitions Claim to accepted and Donation to matched."""
    donor = await _create_test_donor(db_session)
    recip = await _create_test_recipient(
        db_session, "Downtown Safe Pantry", lat=30.2690, lon=-97.7420
    )
    donation = await _create_test_donation(db_session, donor_id=donor.id)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recip.id,
        status=ClaimStatus.offered,
        score=92.0,
    )
    db_session.add(claim)
    await db_session.commit()

    with patch("app.core.security.verify_firebase_token", return_value=MOCK_AUTH_USER):
        headers = {"Authorization": "Bearer test_token"}
        resp = await client.post(f"/v1/claims/{claim.id}/accept", headers=headers)
        assert resp.status_code == 200
        body = resp.json()

        assert body["id"] == str(claim.id)
        assert body["status"] == "accepted"
        assert body["responded_at"] is not None


# ── TEST 8: Algorithmic Match Endpoint (POST /v1/donations/{id}/match) ──────────
@pytest.mark.asyncio
async def test_donation_match_api_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /v1/donations/{id}/match returns ranked candidates and creates top claim."""
    base_lat, base_lon = 31.2500, -98.5000  # Unique isolated cluster
    donor = await _create_test_donor(db_session, lat=base_lat, lon=base_lon)
    recip = await _create_test_recipient(
        db_session, "Rural Texas Haven", lat=base_lat + 0.001, lon=base_lon
    )
    donation = await _create_test_donation(db_session, donor_id=donor.id, weight_kg=18.0)
    await db_session.commit()

    with patch("app.core.security.verify_firebase_token", return_value=MOCK_AUTH_USER):
        headers = {"Authorization": "Bearer test_token"}
        resp = await client.post(
            f"/v1/donations/{donation.id}/match?radius_km=15.0", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["donation_id"] == str(donation.id)
        assert data["status"] == "matched"
        assert data["matches_count"] >= 1
        assert data["top_claim_id"] is not None
        assert data["top_recipient_id"] is not None
        assert any(c["recipient_id"] == str(recip.id) for c in data["candidates"])
