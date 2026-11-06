"""BountyLoop — Autonomous Rescue Agent Test Suite (§Master Plan §6 Phase 8).

Verifies:
1. Tool Suite: candidate search, distribution rebalancing, match proposal, escalation, event logging.
2. ReAct Multi-turn Reasoning: Thought -> Action -> Observation -> Final Decision trace.
3. Autonomous Confidence Gates:
   - High confidence (>= threshold) auto-accepts match.
   - Moderate confidence (< threshold) proposes offer claim for manual confirmation.
4. Safety Gates: Contamination / Formalin hazard flags immediately halt and escalate.
5. Fallback & Escalation: No candidates found triggers human review queue item.
6. Audit Logging: Audit trail persisted in agent_events table.
7. API Endpoints: POST /v1/agent/run, POST /v1/agent/evaluate, GET /v1/agent/events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from geoalchemy2.elements import WKTElement
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.coordinator import AutonomousRescueAgent
from app.agent.tools import (
    tool_escalate_to_human,
    tool_log_agent_event,
    tool_propose_match,
    tool_rebalance_distribution,
    tool_search_candidates,
)
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
    ReviewQueue,
    ReviewReason,
    ReviewStatus,
    User,
    UserRole,
)

MOCK_AGENT_USER = {
    "uid": "fb_agent_operator_01",
    "email": "agent_op@bountyloop.org",
    "name": "Alex Agent Operator",
}


async def _create_agent_test_donor(
    db: AsyncSession,
    lat: float = 32.5000,
    lon: float = -99.5000,
) -> Donor:
    """Helper to persist a test donor in an isolated coordinate space."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"donor_{uuid.uuid4().hex[:8]}",
        email=f"donor_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.donor,
        display_name="West Texas Harvest Donor",
    )
    db.add(user)
    await db.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.grocery,
        address="100 West St, Abilene, TX",
        location=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )
    db.add(donor)
    await db.flush()
    return donor


async def _create_agent_test_recipient(
    db: AsyncSession,
    name: str,
    lat: float,
    lon: float,
    capacity_kg: float = 300.0,
    accepted_items: list[str] | None = None,
    urgency_weight: float = 1.2,
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
        address=f"{name} Warehouse, TX",
        location=WKTElement(f"POINT({lon} {lat})", srid=4326),
        capacity_kg_per_day=capacity_kg,
        accepted_items=accepted_items
        if accepted_items is not None
        else ["produce_fruit", "bread_bakery"],
        is_accepting=True,
        urgency_weight=urgency_weight,
    )
    db.add(recip)
    await db.flush()
    return recip


async def _create_agent_test_donation(
    db: AsyncSession,
    donor_id: uuid.UUID,
    item: FoodCategory = FoodCategory.produce_fruit,
    weight_kg: float = 20.0,
    hazard_flag: HazardFlag = HazardFlag.none,
    hours_to_expiry: float = 24.0,
) -> Donation:
    """Helper to persist a test donation."""
    now = datetime.now(UTC)
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor_id,
        item=item,
        item_confidence=0.95,
        freshness=FreshnessGrade.grade_2_good,
        freshness_confidence=0.91,
        hazard_flag=hazard_flag,
        est_weight_kg=weight_kg,
        expires_at=now + timedelta(hours=hours_to_expiry),
        status=DonationStatus.open,
        needs_review=False,
    )
    db.add(donation)
    await db.flush()
    return donation


# ── TEST 1: Tool search_candidates ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_agent_tool_search_candidates(db_session: AsyncSession) -> None:
    """search_candidates tool filters candidates and provides scores with breakdown."""
    donor = await _create_agent_test_donor(db_session, lat=32.1000, lon=-99.1000)
    recip = await _create_agent_test_recipient(
        db_session, "Abilene Hope Pantry", lat=32.1100, lon=-99.0900
    )
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)

    result = await tool_search_candidates(donation_id=donation.id, radius_km=20.0, db=db_session)

    assert result["total_candidates"] >= 1
    match = next((c for c in result["candidates"] if c["recipient_id"] == str(recip.id)), None)
    assert match is not None
    assert match["distance_km"] > 0
    assert match["score"] > 0
    assert "distance_score" in match["breakdown"]


# ── TEST 2: Tool rebalance_distribution ───────────────────────────────────────
@pytest.mark.asyncio
async def test_agent_tool_rebalance_distribution(db_session: AsyncSession) -> None:
    """rebalance_distribution tool audits consecutive wins across recipients."""
    donor = await _create_agent_test_donor(db_session)
    recip = await _create_agent_test_recipient(
        db_session, "West Texas Pantry", lat=32.5050, lon=-99.4950
    )

    result = await tool_rebalance_distribution(
        recipient_ids=[str(recip.id)], donor_id=donor.id, db=db_session
    )
    assert result["status"] == "audited"
    assert str(recip.id) in result["details"]
    assert result["details"][str(recip.id)]["equity_cleared"] is True


# ── TEST 3: Tool propose_match ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_agent_tool_propose_match_and_auto_accept(db_session: AsyncSession) -> None:
    """propose_match persists claim, records rationale, and transitions status on auto_accept."""
    donor = await _create_agent_test_donor(db_session)
    recip = await _create_agent_test_recipient(
        db_session, "Target Food Shelter", lat=32.5100, lon=-99.4900
    )
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)

    rationale = "Candidate is 1.2km away with 300kg daily capacity headroom."
    match_result = await tool_propose_match(
        donation_id=donation.id,
        recipient_id=recip.id,
        rationale=rationale,
        score=91.5,
        auto_accept=True,
        db=db_session,
    )

    assert match_result["status"] == "accepted"
    assert match_result["auto_accepted"] is True
    assert match_result["rationale"] == rationale

    # Verify Claim in DB
    claim_id = uuid.UUID(match_result["claim_id"])
    stmt = select(Claim).where(Claim.id == claim_id)
    claim = (await db_session.execute(stmt)).scalar_one()
    assert claim.status == ClaimStatus.accepted
    assert claim.score_breakdown["agent_rationale"] == rationale

    # Verify Donation transitioned to matched
    assert donation.status == DonationStatus.matched


# ── TEST 4: Tool escalate_to_human ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_agent_tool_escalate_to_human(db_session: AsyncSession) -> None:
    """escalate_to_human flags donation and creates pending ReviewQueue entry."""
    donor = await _create_agent_test_donor(db_session)
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)

    rationale = "Ambiguous candidate scores or out-of-range dispatch needed."
    escalation = await tool_escalate_to_human(
        donation_id=donation.id,
        reason=ReviewReason.ambiguous_match,
        rationale=rationale,
        db=db_session,
    )

    assert escalation["status"] == "pending_human_review"
    assert escalation["reason"] == "ambiguous_match"

    rq_id = uuid.UUID(escalation["review_queue_id"])
    rq_stmt = select(ReviewQueue).where(ReviewQueue.id == rq_id)
    rq_item = (await db_session.execute(rq_stmt)).scalar_one()
    assert rq_item.status == ReviewStatus.pending
    assert donation.needs_review is True


# ── TEST 5: Tool log_agent_event ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_agent_tool_log_agent_event(db_session: AsyncSession) -> None:
    """log_agent_event creates immutable audit row in agent_events table."""
    donor = await _create_agent_test_donor(db_session)
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)

    payload = {"test_metric": 42, "reasoning": "High confidence match verified"}
    event = await tool_log_agent_event(
        event_type="agent_test_decision",
        payload=payload,
        donation_id=donation.id,
        model="claude-3-5-sonnet",
        latency_ms=120,
        db=db_session,
    )

    assert event.id is not None
    assert event.event_type == "agent_test_decision"
    assert event.payload["test_metric"] == 42
    assert event.latency_ms == 120


# ── TEST 6: ReAct Loop High Confidence Auto-Accept ────────────────────────────
@pytest.mark.asyncio
async def test_agent_react_loop_high_confidence_auto_accept(db_session: AsyncSession) -> None:
    """Agent autonomously matches and auto-accepts when confidence >= threshold."""
    import random

    jitter = random.uniform(0.1, 5.0)
    base_lat, base_lon = 34.1000 + jitter, -102.8000 - jitter
    donor = await _create_agent_test_donor(db_session, lat=base_lat, lon=base_lon)
    recip = await _create_agent_test_recipient(
        db_session,
        "Primary Regional Shelter",
        lat=base_lat + 0.002,
        lon=base_lon,
        capacity_kg=500.0,
    )
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id, weight_kg=15.0)

    agent = AutonomousRescueAgent(default_auto_accept_threshold=75.0)
    run_result = await agent.run(
        donation_id=donation.id,
        db=db_session,
        auto_accept_threshold=75.0,
    )

    assert run_result["action_taken"] == "auto_matched"
    assert run_result["claim_id"] is not None
    assert run_result["recipient_id"] == str(recip.id)
    assert run_result["confidence_score"] >= 75.0
    assert len(run_result["trace"]) >= 3
    assert run_result["event_id"] is not None

    # Verify ReAct trace structure
    steps = [t["action"] for t in run_result["trace"]]
    assert "search_candidates" in steps
    assert "rebalance_distribution" in steps
    assert "propose_match" in steps


# ── TEST 7: ReAct Loop Moderate Confidence Proposes Offer ─────────────────────
@pytest.mark.asyncio
async def test_agent_react_loop_moderate_confidence_proposes_offer(
    db_session: AsyncSession,
) -> None:
    """When confidence is below auto-accept threshold, agent proposes offer for recipient review."""
    import random

    jitter = random.uniform(0.1, 5.0)
    base_lat, base_lon = 36.3000 + jitter, -101.6000 - jitter
    donor = await _create_agent_test_donor(db_session, lat=base_lat, lon=base_lon)
    recip = await _create_agent_test_recipient(
        db_session, "Rural Hub", lat=base_lat + 0.010, lon=base_lon, capacity_kg=300.0
    )
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id, weight_kg=25.0)

    agent = AutonomousRescueAgent()
    # Set high auto-accept threshold to force offer-only proposal
    run_result = await agent.run(
        donation_id=donation.id,
        db=db_session,
        auto_accept_threshold=98.0,
    )

    assert run_result["action_taken"] == "offer_proposed"
    assert run_result["claim_id"] is not None
    assert run_result["recipient_id"] == str(recip.id)

    # Claim should be in offered status, not accepted
    claim = (
        await db_session.execute(select(Claim).where(Claim.id == uuid.UUID(run_result["claim_id"])))
    ).scalar_one()
    assert claim.status == ClaimStatus.offered


# ── TEST 8: Safety Gate Contamination Escalation ───────────────────────────────
@pytest.mark.asyncio
async def test_agent_hazard_flag_triggers_safety_escalation(db_session: AsyncSession) -> None:
    """Hazard flag immediately halts agent matching and escalates to human review."""
    donor = await _create_agent_test_donor(db_session)
    # Donation with chemical formalin hazard
    donation = await _create_agent_test_donation(
        db_session,
        donor_id=donor.id,
        hazard_flag=HazardFlag.suspected_contamination_or_formalin,
    )

    agent = AutonomousRescueAgent()
    run_result = await agent.run(donation_id=donation.id, db=db_session)

    assert run_result["action_taken"] == "escalated_to_human"
    assert run_result["reason"] == "hazard"
    assert run_result["claim_id"] is None
    assert len(run_result["trace"]) == 1
    assert run_result["trace"][0]["action"] == "escalate_to_human"
    assert run_result["event_id"] is not None


# ── TEST 9: No Candidates Fallback Escalation ──────────────────────────────────
@pytest.mark.asyncio
async def test_agent_no_candidates_fallback_escalation(db_session: AsyncSession) -> None:
    """When no eligible candidates are in radius, agent escalates to human operator."""
    # Remote location with no nearby recipients
    donor = await _create_agent_test_donor(db_session, lat=35.0000, lon=-101.5000)
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)

    agent = AutonomousRescueAgent()
    run_result = await agent.run(donation_id=donation.id, db=db_session, radius_km=2.0)

    assert run_result["action_taken"] == "escalated_to_human"
    assert run_result["claim_id"] is None
    assert any(t["action"] == "escalate_to_human" for t in run_result["trace"])


# ── TEST 10: API Endpoints (POST /run, POST /evaluate, GET /events) ────────────
@pytest.mark.asyncio
async def test_agent_api_endpoints_run_evaluate_and_events(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """API endpoints for agent run, dry-run evaluate, and audit events query."""
    base_lat, base_lon = 33.6000, -99.4000
    donor = await _create_agent_test_donor(db_session, lat=base_lat, lon=base_lon)
    await _create_agent_test_recipient(
        db_session, "API Test Shelter", lat=base_lat + 0.005, lon=base_lon
    )
    donation = await _create_agent_test_donation(db_session, donor_id=donor.id)
    await db_session.commit()

    with patch("app.core.security.verify_firebase_token", return_value=MOCK_AGENT_USER):
        headers = {"Authorization": "Bearer agent_token"}

        # 1. POST /v1/agent/evaluate (Dry-run mode)
        eval_resp = await client.post(
            "/v1/agent/evaluate",
            headers=headers,
            json={"donation_id": str(donation.id), "radius_km": 15.0},
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["dry_run"] is True
        assert eval_data["action_taken"] in ("auto_matched", "offer_proposed")
        assert len(eval_data["trace"]) > 0

        # Verify dry run did NOT create a claim in the database
        claims_stmt = select(Claim).where(Claim.donation_id == donation.id)
        claims = (await db_session.execute(claims_stmt)).scalars().all()
        assert len(claims) == 0

        # 2. POST /v1/agent/run (Live execution)
        run_resp = await client.post(
            "/v1/agent/run",
            headers=headers,
            json={
                "donation_id": str(donation.id),
                "radius_km": 15.0,
                "auto_accept_threshold": 70.0,
            },
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data["dry_run"] is False
        assert run_data["action_taken"] == "auto_matched"
        assert run_data["claim_id"] is not None
        assert run_data["event_id"] is not None

        # 3. GET /v1/agent/events (Audit log)
        events_resp = await client.get(
            f"/v1/agent/events?donation_id={donation.id}",
            headers=headers,
        )
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert len(events) >= 1
        assert events[0]["donation_id"] == str(donation.id)
        assert "payload" in events[0]
