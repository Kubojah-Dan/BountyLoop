"""BountyLoop — Autonomous Rescue Agent Tool Suite (§Master Plan §6 Phase 8).

Implements sandboxed tools:
- search_candidates: PostGIS candidate filtering and scoring
- propose_match: Creates and optionally auto-accepts claim
- rebalance_distribution: Regional equity analysis
- log_agent_event: Audit trail persistence
- escalate_to_human: Human review queue escalation
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AgentEvent,
    Claim,
    ClaimStatus,
    Donation,
    DonationStatus,
    Donor,
    Recipient,
    ReviewQueue,
    ReviewReason,
    ReviewStatus,
)
from app.services.matching import get_recipient_consecutive_wins, matching_engine
from app.services.notification import notification_service
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


async def tool_search_candidates(
    donation_id: uuid.UUID,
    radius_km: float = 25.0,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Search, filter, and score eligible candidate recipients using PostGIS matching engine."""
    if db is None:
        raise ValueError("Database session required for candidate search")

    stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == donation_id)
    )
    res = await db.execute(stmt)
    donation = res.scalar_one_or_none()

    if not donation:
        return {"error": f"Donation '{donation_id}' not found", "candidates": []}

    candidates = await matching_engine.find_candidates(
        donation=donation,
        db=db,
        radius_km=radius_km,
        enforce_equity=True,
    )

    serialized = []
    for c in candidates:
        name = (
            c.recipient.user.display_name or c.recipient.user.org_name or "Food Rescue Partner"
            if c.recipient.user
            else "Food Rescue Partner"
        )
        serialized.append(
            {
                "recipient_id": str(c.recipient.id),
                "name": name,
                "address": c.recipient.address,
                "distance_km": c.distance_km,
                "capacity_kg_per_day": float(c.recipient.capacity_kg_per_day),
                "score": c.score,
                "breakdown": c.breakdown,
            }
        )

    return {
        "donation_id": str(donation_id),
        "item": donation.item.value,
        "est_weight_kg": float(donation.est_weight_kg),
        "total_candidates": len(serialized),
        "candidates": serialized,
    }


async def tool_rebalance_distribution(
    recipient_ids: list[str],
    donor_id: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Audit recipient win frequency to preserve community equity across regional food pantries."""
    if db is None:
        raise ValueError("Database session required for distribution rebalancing")

    rebalance_report: dict[str, Any] = {}
    for r_id_str in recipient_ids:
        try:
            r_uuid = uuid.UUID(r_id_str)
            streak = await get_recipient_consecutive_wins(r_uuid, db, donor_id=donor_id)
            rebalance_report[r_id_str] = {
                "consecutive_wins": streak,
                "equity_cleared": streak < matching_engine.max_consecutive_wins,
                "cap": matching_engine.max_consecutive_wins,
            }
        except Exception as e:
            logger.warning("Error auditing recipient %s equity: %s", r_id_str, e)

    return {
        "status": "audited",
        "recipients_evaluated": len(rebalance_report),
        "details": rebalance_report,
    }


async def tool_propose_match(
    donation_id: uuid.UUID,
    recipient_id: uuid.UUID,
    rationale: str,
    score: float = 90.0,
    score_breakdown: dict[str, Any] | None = None,
    auto_accept: bool = False,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Persist a matched Claim entity with rationale and optional autonomous auto-acceptance."""
    if db is None:
        raise ValueError("Database session required for match proposal")

    # Load donation
    d_stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == donation_id)
    )
    donation = (await db.execute(d_stmt)).scalar_one_or_none()
    if not donation:
        return {"error": f"Donation '{donation_id}' not found"}

    # Load recipient
    r_stmt = (
        select(Recipient).options(selectinload(Recipient.user)).where(Recipient.id == recipient_id)
    )
    recipient = (await db.execute(r_stmt)).scalar_one_or_none()
    if not recipient:
        return {"error": f"Recipient '{recipient_id}' not found"}

    now = datetime.now(UTC)
    breakdown = dict(score_breakdown or {})
    breakdown["agent_rationale"] = rationale
    breakdown["auto_accepted"] = auto_accept

    target_status = ClaimStatus.accepted if auto_accept else ClaimStatus.offered

    # Check for existing pending claim
    c_stmt = select(Claim).where(
        Claim.donation_id == donation_id,
        Claim.recipient_id == recipient_id,
        Claim.status.in_([ClaimStatus.offered, ClaimStatus.accepted]),
    )
    existing_claim = (await db.execute(c_stmt)).scalar_one_or_none()

    if existing_claim:
        claim = existing_claim
        claim.status = target_status
        claim.score = score
        claim.score_breakdown = breakdown
        if auto_accept:
            claim.responded_at = now
    else:
        claim = Claim(
            id=uuid.uuid4(),
            donation_id=donation_id,
            recipient_id=recipient_id,
            status=target_status,
            score=score,
            score_breakdown=breakdown,
            offered_at=now,
            responded_at=now if auto_accept else None,
        )
        db.add(claim)

    if auto_accept:
        donation.status = DonationStatus.matched

    await db.commit()
    await db.refresh(claim)

    # Notify donor
    if donation.donor and donation.donor.user:
        recipient_name = (
            recipient.user.display_name or recipient.user.org_name or "Verified Food Rescue Partner"
            if recipient.user
            else "Verified Food Rescue Partner"
        )
        await notification_service.notify_donation_claimed(
            db=db,
            donor_user_id=donation.donor.user.id,
            donation_id=donation.id,
            claim_id=claim.id,
            recipient_name=recipient_name,
            item_name=donation.item.value,
        )

    # Broadcast event
    await ws_manager.broadcast(
        "donation_matched" if auto_accept else "offer_created",
        {
            "claim_id": str(claim.id),
            "donation_id": str(donation.id),
            "recipient_id": str(recipient.id),
            "status": claim.status.value,
            "score": float(claim.score),
            "rationale": rationale,
        },
    )

    return {
        "claim_id": str(claim.id),
        "donation_id": str(donation.id),
        "recipient_id": str(recipient.id),
        "status": claim.status.value,
        "auto_accepted": auto_accept,
        "score": float(claim.score),
        "rationale": rationale,
    }


async def tool_escalate_to_human(
    donation_id: uuid.UUID,
    reason: ReviewReason = ReviewReason.ambiguous_match,
    rationale: str = "Escalated by autonomous rescue coordinator agent",
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Escalate donation to human operator review queue when match confidence is low."""
    if db is None:
        raise ValueError("Database session required for human escalation")

    d_stmt = select(Donation).where(Donation.id == donation_id)
    donation = (await db.execute(d_stmt)).scalar_one_or_none()
    if not donation:
        return {"error": f"Donation '{donation_id}' not found"}

    donation.needs_review = True

    # Check for existing review item
    rq_stmt = select(ReviewQueue).where(
        ReviewQueue.donation_id == donation_id,
        ReviewQueue.status == ReviewStatus.pending,
    )
    review_item = (await db.execute(rq_stmt)).scalar_one_or_none()

    if not review_item:
        review_item = ReviewQueue(
            id=uuid.uuid4(),
            donation_id=donation_id,
            reason=reason,
            status=ReviewStatus.pending,
        )
        db.add(review_item)

    await db.commit()
    await db.refresh(review_item)

    await ws_manager.broadcast(
        "donation_needs_review",
        {
            "donation_id": str(donation_id),
            "review_queue_id": str(review_item.id),
            "reason": reason.value,
            "rationale": rationale,
        },
    )

    return {
        "review_queue_id": str(review_item.id),
        "donation_id": str(donation_id),
        "reason": reason.value,
        "status": "pending_human_review",
        "rationale": rationale,
    }


async def tool_log_agent_event(
    event_type: str,
    payload: dict[str, Any],
    donation_id: uuid.UUID | None = None,
    model: str = "claude-3-5-sonnet",
    latency_ms: int = 0,
    db: AsyncSession | None = None,
) -> AgentEvent:
    """Persist an auditable agent event into PostgreSQL agent_events table."""
    if db is None:
        raise ValueError("Database session required for logging agent events")

    event = AgentEvent(
        id=uuid.uuid4(),
        donation_id=donation_id,
        event_type=event_type,
        payload=payload,
        model=model,
        latency_ms=latency_ms,
        created_at=datetime.now(UTC),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    logger.info(
        "Persisted AgentEvent '%s' (id=%s) for donation=%s", event_type, event.id, donation_id
    )
    return event
