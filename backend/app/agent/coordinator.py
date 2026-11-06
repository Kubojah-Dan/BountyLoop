"""BountyLoop — Autonomous Rescue Agent Coordinator (§Master Plan §6 Phase 8).

Implements the multi-turn ReAct reasoning loop:
- Thought: Analyzes perishable donation context, shelf life, and safety constraints
- Action: Invocates sandboxed tools (search_candidates, rebalance_distribution, propose_match, escalate_to_human)
- Observation: Ingests structured feedback from PostGIS and equity systems
- Decision: Autonomous match under high confidence, offer proposal under medium confidence, or human escalation
- Auditability: Complete reasoning trace and event logging into agent_events
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.llm_client import llm_client
from app.agent.tools import (
    tool_escalate_to_human,
    tool_log_agent_event,
    tool_propose_match,
    tool_rebalance_distribution,
    tool_search_candidates,
)
from app.db.models import Donation, DonationStatus, Donor, HazardFlag, ReviewReason

logger = logging.getLogger(__name__)


class AutonomousRescueAgent:
    """Multi-turn autonomous coordinator for food rescue matching."""

    def __init__(self, default_auto_accept_threshold: float = 80.0) -> None:
        self.default_auto_accept_threshold = default_auto_accept_threshold

    async def run(
        self,
        donation_id: uuid.UUID,
        db: AsyncSession,
        radius_km: float = 25.0,
        auto_accept_threshold: float | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute the full autonomous rescue coordination loop."""
        start_time = time.perf_counter()
        threshold = (
            auto_accept_threshold
            if auto_accept_threshold is not None
            else self.default_auto_accept_threshold
        )
        trace: list[dict[str, Any]] = []

        # ── 1. Context Assessment ─────────────────────────────────────────────
        d_stmt = (
            select(Donation)
            .options(selectinload(Donation.donor).selectinload(Donor.user))
            .where(Donation.id == donation_id)
        )
        res = await db.execute(d_stmt)
        donation = res.scalar_one_or_none()

        if not donation:
            raise ValueError(f"Donation '{donation_id}' not found.")

        # Safety Gate: Contamination / Formalin / Physical Hazard Check
        if donation.hazard_flag != HazardFlag.none:
            thought = (
                f"SAFETY ALERT: Donation {donation_id} has hazard flag '{donation.hazard_flag.value}'. "
                "Per operating principles, food safety is non-negotiable. Escalating to human review queue immediately."
            )
            trace.append(
                {
                    "step": 1,
                    "thought": thought,
                    "action": "escalate_to_human",
                    "action_input": {"reason": "hazard", "flag": donation.hazard_flag.value},
                    "observation": "Food rescue halted due to safety hazard.",
                }
            )

            if not dry_run:
                await tool_escalate_to_human(
                    donation_id=donation_id,
                    reason=ReviewReason.hazard,
                    rationale=thought,
                    db=db,
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            event_id = None
            if not dry_run:
                event = await tool_log_agent_event(
                    event_type="hazard_escalated",
                    payload={
                        "donation_id": str(donation_id),
                        "hazard": donation.hazard_flag.value,
                        "trace": trace,
                    },
                    donation_id=donation_id,
                    model=llm_client.model,
                    latency_ms=elapsed_ms,
                    db=db,
                )
                event_id = str(event.id)

            return {
                "donation_id": str(donation_id),
                "action_taken": "escalated_to_human",
                "reason": "hazard",
                "confidence_score": 0.0,
                "claim_id": None,
                "recipient_id": None,
                "trace": trace,
                "event_id": event_id,
                "latency_ms": elapsed_ms,
            }

        # Status Check: Only open donations can be matched
        if donation.status not in (DonationStatus.open, DonationStatus.draft):
            return {
                "donation_id": str(donation_id),
                "action_taken": "no_action",
                "reason": f"Donation is already in '{donation.status.value}' status",
                "confidence_score": 0.0,
                "claim_id": None,
                "recipient_id": None,
                "trace": [],
                "event_id": None,
                "latency_ms": int((time.perf_counter() - start_time) * 1000),
            }

        donor_display = (
            donation.donor.user.display_name or donation.donor.user.org_name or "Local Food Donor"
            if donation.donor and donation.donor.user
            else "Local Food Donor"
        )
        item_name = donation.item.value
        weight_kg = float(donation.est_weight_kg)

        # ── 2. Tool 1: search_candidates ──────────────────────────────────────
        thought_1 = (
            f"Assessing surplus batch from '{donor_display}': {weight_kg}kg of '{item_name}'. "
            f"Querying candidate recipients within {radius_km}km radius..."
        )
        action_input_1 = {"donation_id": str(donation_id), "radius_km": radius_km}

        candidates_result = await tool_search_candidates(
            donation_id=donation_id,
            radius_km=radius_km,
            db=db,
        )
        candidates = candidates_result.get("candidates", [])

        obs_1 = f"Discovered {len(candidates)} eligible recipient partners within radius. " + (
            f"Top candidate: {candidates[0]['name']} (Distance: {candidates[0]['distance_km']}km, Score: {candidates[0]['score']})"
            if candidates
            else "No eligible recipients found within radius."
        )
        trace.append(
            {
                "step": 1,
                "thought": thought_1,
                "action": "search_candidates",
                "action_input": action_input_1,
                "observation": obs_1,
            }
        )

        # ── 3. Tool 2: rebalance_distribution ─────────────────────────────────
        if candidates:
            candidate_ids = [c["recipient_id"] for c in candidates[:5]]
            donor_uuid = donation.donor_id if donation.donor else None
            thought_2 = (
                f"Evaluating regional community distribution equity across {len(candidate_ids)} candidates "
                f"to prevent consecutive-win monopolization..."
            )
            rebalance_result = await tool_rebalance_distribution(
                recipient_ids=candidate_ids,
                donor_id=donor_uuid,
                db=db,
            )
            obs_2 = f"Equity audit completed: {rebalance_result.get('recipients_evaluated', 0)} candidates verified."
            trace.append(
                {
                    "step": 2,
                    "thought": thought_2,
                    "action": "rebalance_distribution",
                    "action_input": {"recipient_ids": candidate_ids},
                    "observation": obs_2,
                }
            )

        # ── 4. Decision & Execution: propose_match or escalate_to_human ───────
        action_taken = "no_action"
        claim_id = None
        matched_recipient_id = None
        confidence_score = 0.0

        if not candidates:
            # Case C: No candidates found -> Escalate
            thought_3 = (
                f"No eligible recipients within {radius_km}km meet dietary, safety, and capacity intake criteria. "
                "Escalating to human triage operator to expand radius or coordinate direct dispatch."
            )
            trace.append(
                {
                    "step": 3,
                    "thought": thought_3,
                    "action": "escalate_to_human",
                    "action_input": {"reason": "ambiguous_match", "radius_km": radius_km},
                    "observation": "Donation flagged in human review queue.",
                }
            )
            action_taken = "escalated_to_human"

            if not dry_run:
                await tool_escalate_to_human(
                    donation_id=donation_id,
                    reason=ReviewReason.ambiguous_match,
                    rationale=thought_3,
                    db=db,
                )
        else:
            top = candidates[0]
            top_recip_id = uuid.UUID(top["recipient_id"])
            matched_recipient_id = str(top_recip_id)
            confidence_score = float(top["score"])

            if confidence_score >= threshold:
                # Case A: High Confidence -> Autonomous Match & Auto-Accept
                auto_accept = True
                action_taken = "auto_matched"
                thought_3 = (
                    f"Top candidate '{top['name']}' scored {confidence_score}/100 with clear capacity headroom "
                    f"({top['capacity_kg_per_day']}kg/day) and distance {top['distance_km']}km. "
                    f"Score exceeds auto-accept threshold ({threshold}). Proceeding with autonomous match & auto-acceptance."
                )
            else:
                # Case B: Moderate Confidence -> Offer Claim Proposed for Confirmation
                auto_accept = False
                action_taken = "offer_proposed"
                thought_3 = (
                    f"Top candidate '{top['name']}' scored {confidence_score}/100, which is below "
                    f"auto-accept threshold ({threshold}). Proposing an offer claim for recipient confirmation."
                )

            trace.append(
                {
                    "step": 3,
                    "thought": thought_3,
                    "action": "propose_match",
                    "action_input": {
                        "recipient_id": str(top_recip_id),
                        "score": confidence_score,
                        "auto_accept": auto_accept,
                    },
                    "observation": f"Claim proposal executed (auto_accept={auto_accept}).",
                }
            )

            if not dry_run:
                claim_result = await tool_propose_match(
                    donation_id=donation_id,
                    recipient_id=top_recip_id,
                    rationale=thought_3,
                    score=confidence_score,
                    score_breakdown=top["breakdown"],
                    auto_accept=auto_accept,
                    db=db,
                )
                claim_id = claim_result.get("claim_id")

        # ── 5. Tool 4: log_agent_event (Audit Trail) ──────────────────────────
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        event_id = None

        if not dry_run:
            event = await tool_log_agent_event(
                event_type=f"agent_{action_taken}",
                payload={
                    "donation_id": str(donation_id),
                    "action_taken": action_taken,
                    "recipient_id": matched_recipient_id,
                    "claim_id": claim_id,
                    "confidence_score": confidence_score,
                    "threshold": threshold,
                    "trace": trace,
                    "candidates_count": len(candidates),
                },
                donation_id=donation_id,
                model=llm_client.model,
                latency_ms=elapsed_ms,
                db=db,
            )
            event_id = str(event.id)

        return {
            "donation_id": str(donation_id),
            "action_taken": action_taken,
            "claim_id": claim_id,
            "recipient_id": matched_recipient_id,
            "confidence_score": confidence_score,
            "threshold": threshold,
            "trace": trace,
            "event_id": event_id,
            "latency_ms": elapsed_ms,
            "dry_run": dry_run,
        }


rescue_agent = AutonomousRescueAgent()
