"""BountyLoop — Recipient Matching Engine (§Master Plan §6 Phase 7).

Automates candidate discovery and transparent multi-factor scoring:
- PostGIS spatial filtering (ST_DWithin radius)
- Recipient intake acceptance check (is_accepting == True)
- Dietary/category compatibility (accepted_items)
- Rescue capacity headroom (capacity_kg_per_day >= est_weight_kg)
- Consecutive-win equity guard (MAX_CONSECUTIVE_WINS) to prevent monopolization
- Multi-factor scoring configured via matching_weights.yaml
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Claim,
    ClaimStatus,
    Donation,
    Donor,
    Recipient,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "core" / "matching_weights.yaml"


def load_matching_config() -> dict[str, Any]:
    """Load matching weights and equity constraints from YAML."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning("Failed to parse matching_weights.yaml (%s); using defaults", e)

    return {
        "weights": {
            "distance": 0.30,
            "urgency": 0.25,
            "capacity_fit": 0.20,
            "hunger_need": 0.15,
            "reliability": 0.10,
        },
        "equity": {
            "max_consecutive_wins": 3,
            "radius_default_km": 25.0,
            "offer_ttl_minutes": 30,
        },
    }


def extract_lat_lon(location: Any) -> tuple[float, float] | None:
    """Extract (latitude, longitude) from GeoAlchemy2 / PostGIS geometry."""
    if location is None:
        return None
    try:
        shape = to_shape(location)
        return (float(shape.y), float(shape.x))
    except Exception:
        pass
    match = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", str(location), re.IGNORECASE)
    if match:
        lon = float(match.group(1))
        lat = float(match.group(2))
        return (lat, lon)
    return None


async def get_recipient_consecutive_wins(
    recipient_id: uuid.UUID,
    db: AsyncSession,
    donor_id: uuid.UUID | None = None,
) -> int:
    """Count consecutive most recent accepted or picked up claims won by this recipient."""
    stmt = (
        select(Claim.recipient_id)
        .join(Donation, Claim.donation_id == Donation.id)
        .where(Claim.status.in_([ClaimStatus.accepted, ClaimStatus.picked_up]))
    )
    if donor_id is not None:
        stmt = stmt.where(Donation.donor_id == donor_id)

    stmt = stmt.order_by(Claim.offered_at.desc(), Claim.id.desc()).limit(20)
    res = await db.execute(stmt)
    winners = res.scalars().all()
    streak = 0
    for wid in winners:
        if wid == recipient_id:
            streak += 1
        else:
            break
    return streak


async def get_recipient_reliability(recipient_id: uuid.UUID, db: AsyncSession) -> float:
    """Calculate historical pickup completion rate: completed / (completed + declined)."""
    stmt = select(Claim.status).where(
        Claim.recipient_id == recipient_id,
        Claim.status.in_([ClaimStatus.picked_up, ClaimStatus.declined]),
    )
    res = await db.execute(stmt)
    statuses = res.scalars().all()
    if not statuses:
        return 0.95  # Standard baseline reliability for new recipients

    completed = sum(1 for s in statuses if s == ClaimStatus.picked_up)
    return max(0.1, min(1.0, completed / len(statuses)))


@dataclass
class ScoredCandidate:
    """Structured candidate recipient with transparent scoring breakdown."""

    recipient: Recipient
    distance_km: float
    score: float
    breakdown: dict[str, Any]


class MatchingEngine:
    """Fair-allocation matching engine for perishable food donations."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or load_matching_config()
        self.weights = cfg.get(
            "weights",
            {
                "distance": 0.30,
                "urgency": 0.25,
                "capacity_fit": 0.20,
                "hunger_need": 0.15,
                "reliability": 0.10,
            },
        )
        self.equity = cfg.get(
            "equity",
            {
                "max_consecutive_wins": 3,
                "radius_default_km": 25.0,
                "offer_ttl_minutes": 30,
            },
        )
        self.max_consecutive_wins = int(self.equity.get("max_consecutive_wins", 3))
        self.radius_default_km = float(self.equity.get("radius_default_km", 25.0))

    async def find_candidates(
        self,
        donation: Donation,
        db: AsyncSession,
        radius_km: float | None = None,
        enforce_equity: bool = True,
    ) -> list[ScoredCandidate]:
        """Discover, filter, and score eligible candidate recipients for a donation."""
        search_radius_km = radius_km or self.radius_default_km
        search_radius_m = search_radius_km * 1000.0

        donor = donation.donor
        if not donor:
            donor_stmt = select(Donor).where(Donor.id == donation.donor_id)
            donor = (await db.execute(donor_stmt)).scalar_one_or_none()

        if not donor or donor.location is None:
            logger.warning("Donation %s donor lacks geospatial coordinates", donation.id)
            return []

        # 1. PostGIS Query: Active recipients within radius
        stmt = (
            select(
                Recipient,
                func.ST_Distance(Recipient.location, donor.location).label("distance_m"),
            )
            .options(selectinload(Recipient.user))
            .where(
                Recipient.is_accepting.is_(True),
                func.ST_DWithin(Recipient.location, donor.location, search_radius_m),
            )
        )
        res = await db.execute(stmt)
        rows = res.all()

        now = datetime.now(UTC)
        weight_kg = float(donation.est_weight_kg)
        item_val = donation.item.value

        # Time remaining until expiration
        hours_remaining = max(0.0, (donation.expires_at - now).total_seconds() / 3600.0)

        # Compute Urgency Score (S_urg)
        if hours_remaining <= 6.0:
            s_urg = 1.0
        elif hours_remaining >= 48.0:
            s_urg = 0.20
        else:
            s_urg = 1.0 - 0.80 * ((hours_remaining - 6.0) / 42.0)

        candidates: list[ScoredCandidate] = []

        for recip, dist_m in rows:
            dist_m_val = float(dist_m)
            dist_km = round(dist_m_val / 1000.0, 2)

            # Filter 1: Capacity headroom
            capacity_kg = float(recip.capacity_kg_per_day)
            if capacity_kg < weight_kg:
                logger.debug(
                    "Recipient %s capacity %skg < donation %skg; excluded",
                    recip.id,
                    capacity_kg,
                    weight_kg,
                )
                continue

            # Filter 2: Category compatibility
            if recip.accepted_items and item_val not in recip.accepted_items:
                logger.debug("Recipient %s does not accept %s; excluded", recip.id, item_val)
                continue

            # Filter 3: Consecutive-win equity guard
            consecutive_wins = await get_recipient_consecutive_wins(recip.id, db, donor_id=donor.id)
            if enforce_equity and consecutive_wins >= self.max_consecutive_wins:
                logger.info(
                    "Recipient %s reached max consecutive wins (%d >= %d); equity guard applied",
                    recip.id,
                    consecutive_wins,
                    self.max_consecutive_wins,
                )
                continue

            # Compute Distance Score (S_dist)
            s_dist = max(0.0, min(1.0, 1.0 - (dist_km / search_radius_km)))

            # Compute Capacity Fit Score (S_cap)
            ratio = min(1.0, weight_kg / max(1.0, capacity_kg))
            s_cap = max(0.2, min(1.0, 1.0 - abs(ratio - 0.25) * 1.5))

            # Compute Hunger Need Score (S_need)
            urgency_w = float(recip.urgency_weight)
            s_need = max(0.1, min(1.0, urgency_w / 2.0))

            # Compute Reliability Score (S_rel)
            s_rel = await get_recipient_reliability(recip.id, db)

            # Composite Score (0.0 to 100.0)
            composite = 100.0 * (
                self.weights.get("distance", 0.30) * s_dist
                + self.weights.get("urgency", 0.25) * s_urg
                + self.weights.get("capacity_fit", 0.20) * s_cap
                + self.weights.get("hunger_need", 0.15) * s_need
                + self.weights.get("reliability", 0.10) * s_rel
            )
            score = round(composite, 4)

            breakdown = {
                "distance_km": dist_km,
                "distance_score": round(s_dist, 4),
                "urgency_score": round(s_urg, 4),
                "capacity_fit_score": round(s_cap, 4),
                "hunger_need_score": round(s_need, 4),
                "reliability_score": round(s_rel, 4),
                "consecutive_wins": consecutive_wins,
                "weights": self.weights,
            }

            candidates.append(
                ScoredCandidate(
                    recipient=recip,
                    distance_km=dist_km,
                    score=score,
                    breakdown=breakdown,
                )
            )

        # Sort descending by composite score, breaking ties by closer distance
        candidates.sort(key=lambda c: (-c.score, c.distance_km))
        return candidates

    async def match_and_offer(
        self,
        donation_id: uuid.UUID,
        db: AsyncSession,
        radius_km: float | None = None,
        enforce_equity: bool = True,
    ) -> dict[str, Any]:
        """Execute matching for donation and create top candidate Claim in offered status."""
        stmt = (
            select(Donation)
            .options(selectinload(Donation.donor).selectinload(Donor.user))
            .where(Donation.id == donation_id)
        )
        res = await db.execute(stmt)
        donation = res.scalar_one_or_none()

        if not donation:
            raise ValueError(f"Donation '{donation_id}' not found.")

        candidates = await self.find_candidates(
            donation=donation,
            db=db,
            radius_km=radius_km,
            enforce_equity=enforce_equity,
        )

        top_claim = None
        if candidates:
            top = candidates[0]
            # Check if an offered or accepted claim already exists for this donation & recipient
            existing_stmt = select(Claim).where(
                Claim.donation_id == donation.id,
                Claim.recipient_id == top.recipient.id,
                Claim.status.in_([ClaimStatus.offered, ClaimStatus.accepted]),
            )
            existing_claim = (await db.execute(existing_stmt)).scalar_one_or_none()

            if not existing_claim:
                now = datetime.now(UTC)
                top_claim = Claim(
                    id=uuid.uuid4(),
                    donation_id=donation.id,
                    recipient_id=top.recipient.id,
                    status=ClaimStatus.offered,
                    score=top.score,
                    score_breakdown=top.breakdown,
                    offered_at=now,
                )
                db.add(top_claim)
                await db.commit()
                await db.refresh(top_claim)
            else:
                top_claim = existing_claim

        serialized_candidates = [
            {
                "recipient_id": str(c.recipient.id),
                "recipient_name": (
                    c.recipient.user.display_name
                    or c.recipient.user.org_name
                    or "Food Rescue Partner"
                )
                if c.recipient.user
                else "Food Rescue Partner",
                "recipient_address": c.recipient.address,
                "distance_km": c.distance_km,
                "score": c.score,
                "score_breakdown": c.breakdown,
            }
            for c in candidates
        ]

        return {
            "donation_id": str(donation.id),
            "status": "matched" if top_claim else "no_match",
            "matches_count": len(candidates),
            "top_claim_id": str(top_claim.id) if top_claim else None,
            "top_recipient_id": str(candidates[0].recipient.id) if candidates else None,
            "top_score": candidates[0].score if candidates else None,
            "candidates": serialized_candidates,
        }


matching_engine = MatchingEngine()
