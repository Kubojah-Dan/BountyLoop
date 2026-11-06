"""BountyLoop — Claims & Pickup Lifecycle Endpoints.

Implements food rescue offer claiming, rejection, and pickup verification with impact logging
and real-time notifications (§6 Phase 6).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.models import (
    Claim,
    ClaimStatus,
    Donation,
    DonationStatus,
    Donor,
    ImpactLog,
    Recipient,
    RecipientOrgType,
    User,
    UserRole,
)
from app.db.session import get_db
from app.schemas.claim import ClaimCreate, ClaimDecline, ClaimPickup, ClaimRead
from app.schemas.donation import DonationRead
from app.services.impact import co2e_avoided, meals_equivalent
from app.services.notification import notification_service
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])


async def _get_or_create_recipient(user: User, db: AsyncSession) -> Recipient:
    """Retrieve or auto-provision recipient profile for the current user."""
    stmt = select(Recipient).where(Recipient.user_id == user.id)
    res = await db.execute(stmt)
    recipient = res.scalar_one_or_none()
    if recipient:
        return recipient

    # Auto-provision recipient profile (default Austin location)
    recipient = Recipient(
        id=uuid.uuid4(),
        user_id=user.id,
        org_type=RecipientOrgType.food_bank,
        address=user.org_name or "Austin, TX",
        location=WKTElement("POINT(-97.7431 30.2672)", srid=4326),
        capacity_kg_per_day=500.0,
        accepted_items=[
            "produce_fruit",
            "produce_vegetable",
            "bread_bakery",
            "dairy",
            "grains_staples",
        ],
        cold_chain=True,
        urgency_weight=1.0,
        is_accepting=True,
    )
    db.add(recipient)
    await db.flush()
    logger.info("Auto-provisioned Recipient profile %s for user %s", recipient.id, user.id)
    return recipient


def _build_claim_read(claim: Claim, impact_record: ImpactLog | None = None) -> ClaimRead:
    """Format Claim entity into response schema with populated donation and donor info."""
    donation_read = None
    donor_name = None
    recipient_name = None

    if claim.recipient and claim.recipient.user:
        recipient_name = claim.recipient.user.display_name or claim.recipient.user.org_name

    if claim.donation:
        if claim.donation.donor and claim.donation.donor.user:
            donor_name = (
                claim.donation.donor.user.display_name or claim.donation.donor.user.org_name
            )

        donor_address = claim.donation.donor.address if claim.donation.donor else None
        donation_read = DonationRead(
            id=claim.donation.id,
            donor_id=claim.donation.donor_id,
            photo_paths=list(claim.donation.photo_paths or []),
            item=claim.donation.item,
            item_confidence=float(claim.donation.item_confidence),
            freshness=claim.donation.freshness,
            freshness_confidence=float(claim.donation.freshness_confidence),
            hazard_flag=claim.donation.hazard_flag,
            est_weight_kg=float(claim.donation.est_weight_kg),
            expires_at=claim.donation.expires_at,
            status=claim.donation.status,
            needs_review=claim.donation.needs_review,
            model_versions=claim.donation.model_versions,
            created_at=claim.donation.created_at,
            donor_name=donor_name,
            donor_address=donor_address,
        )

    impact_dict = None
    if impact_record:
        impact_dict = {
            "kg_rescued": float(impact_record.kg_rescued),
            "meals_equivalent": float(impact_record.meals_equivalent),
            "co2e_avoided_kg": float(impact_record.co2e_avoided_kg),
        }
    elif claim.donation:
        from sqlalchemy.orm import attributes

        try:
            state = attributes.instance_state(claim.donation)
            if "impact_log" in state.dict and state.dict["impact_log"] is not None:
                log = state.dict["impact_log"]
                impact_dict = {
                    "kg_rescued": float(log.kg_rescued),
                    "meals_equivalent": float(log.meals_equivalent),
                    "co2e_avoided_kg": float(log.co2e_avoided_kg),
                }
        except Exception:
            pass

    return ClaimRead(
        id=claim.id,
        donation_id=claim.donation_id,
        recipient_id=claim.recipient_id,
        recipient_name=recipient_name,
        donor_name=donor_name,
        status=claim.status,
        score=float(claim.score),
        score_breakdown=claim.score_breakdown,
        offered_at=claim.offered_at,
        responded_at=claim.responded_at,
        picked_up_at=claim.picked_up_at,
        proof_photo_path=claim.proof_photo_path,
        donation=donation_read,
        impact=impact_dict,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Claim an open surplus donation",
    response_model=ClaimRead,
)
async def create_claim(
    payload: ClaimCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimRead:
    """Recipient claims an available surplus donation."""
    recipient = await _get_or_create_recipient(current_user, db)

    # Load donation with donor context
    stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == payload.donation_id)
        .with_for_update()
    )
    res = await db.execute(stmt)
    donation = res.scalar_one_or_none()

    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation '{payload.donation_id}' not found.",
        )

    if donation.status != DonationStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Donation is in '{donation.status.value}' status and cannot be claimed.",
        )

    if donation.needs_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donation is currently undergoing safety/quality review and cannot be claimed.",
        )

    # 1. Update donation status to matched
    donation.status = DonationStatus.matched
    now = datetime.now(UTC)

    # 2. Create Claim row
    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.accepted,
        score=95.0,
        score_breakdown={"manual_claim": True},
        offered_at=now,
        responded_at=now,
    )
    db.add(claim)
    await db.commit()

    # Reload claim with eager-loaded relations
    claim_stmt = (
        select(Claim)
        .options(
            selectinload(Claim.donation).selectinload(Donation.donor).selectinload(Donor.user),
            selectinload(Claim.donation).selectinload(Donation.impact_log),
            selectinload(Claim.recipient).selectinload(Recipient.user),
        )
        .where(Claim.id == claim.id)
    )
    loaded_claim = (await db.execute(claim_stmt)).scalar_one()

    # 3. Notify donor via push notification
    if donation.donor and donation.donor.user:
        recipient_display = (
            current_user.display_name or current_user.org_name or "A verified food rescue partner"
        )
        await notification_service.notify_donation_claimed(
            db=db,
            donor_user_id=donation.donor.user.id,
            donation_id=donation.id,
            claim_id=claim.id,
            recipient_name=recipient_display,
            item_name=donation.item.value,
        )

    # 4. Broadcast live update
    response_data = _build_claim_read(loaded_claim)
    await ws_manager.broadcast("donation_matched", response_data.model_dump(mode="json"))

    return response_data


@router.get(
    "",
    summary="List claims for current user (mine)",
    response_model=list[ClaimRead],
)
async def list_claims(
    role: Annotated[str, Query()] = "mine",
    status_filter: Annotated[ClaimStatus | None, Query(alias="status")] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ClaimRead]:
    """Retrieve claims related to current user (as recipient or donor)."""
    query = (
        select(Claim)
        .options(
            selectinload(Claim.donation).selectinload(Donation.donor).selectinload(Donor.user),
            selectinload(Claim.donation).selectinload(Donation.impact_log),
            selectinload(Claim.recipient).selectinload(Recipient.user),
        )
        .order_by(Claim.offered_at.desc())
    )

    if current_user.role == UserRole.recipient:
        recip_stmt = select(Recipient.id).where(Recipient.user_id == current_user.id)
        recip_id = (await db.execute(recip_stmt)).scalar_one_or_none()
        if not recip_id:
            return []
        query = query.where(Claim.recipient_id == recip_id)
    elif current_user.role == UserRole.donor:
        donor_stmt = select(Donor.id).where(Donor.user_id == current_user.id)
        donor_id = (await db.execute(donor_stmt)).scalar_one_or_none()
        if not donor_id:
            return []
        query = query.join(Donation, Claim.donation_id == Donation.id).where(
            Donation.donor_id == donor_id
        )

    if status_filter is not None:
        query = query.where(Claim.status == status_filter)

    results = (await db.execute(query)).scalars().all()
    return [_build_claim_read(cl) for cl in results]


@router.post(
    "/{claim_id}/decline",
    summary="Decline an offered or accepted claim",
    response_model=dict,
)
async def decline_claim(
    claim_id: uuid.UUID,
    payload: ClaimDecline,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Decline a claim, resetting the donation back to open status."""
    stmt = select(Claim).options(selectinload(Claim.donation)).where(Claim.id == claim_id)
    claim = (await db.execute(stmt)).scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found.",
        )

    claim.status = ClaimStatus.declined
    claim.responded_at = datetime.now(UTC)
    if payload.reason:
        score_bd = dict(claim.score_breakdown or {})
        score_bd["decline_reason"] = payload.reason
        claim.score_breakdown = score_bd

    # Reset donation back to open
    if claim.donation:
        claim.donation.status = DonationStatus.open

    await db.commit()
    await ws_manager.broadcast(
        "claim_declined",
        {"claim_id": str(claim.id), "donation_id": str(claim.donation_id)},
    )
    return {"status": "declined", "claim_id": str(claim.id)}


@router.post(
    "/{claim_id}/pickup",
    summary="Confirm donation pickup and record environmental impact",
    response_model=ClaimRead,
)
async def confirm_pickup(
    claim_id: uuid.UUID,
    payload: ClaimPickup,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimRead:
    """Confirm food rescue pickup, closing the loop and persisting impact metrics."""
    stmt = (
        select(Claim)
        .options(
            selectinload(Claim.donation).selectinload(Donation.donor).selectinload(Donor.user),
            selectinload(Claim.recipient).selectinload(Recipient.user),
        )
        .where(Claim.id == claim_id)
    )
    claim = (await db.execute(stmt)).scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found.",
        )

    now = datetime.now(UTC)
    claim.status = ClaimStatus.picked_up
    claim.picked_up_at = now
    if payload.proof_photo_path:
        claim.proof_photo_path = payload.proof_photo_path

    donation = claim.donation
    donation.status = DonationStatus.completed

    # Calculate and persist ImpactLog row
    kg = float(donation.est_weight_kg)
    meals = meals_equivalent(kg)
    co2e = co2e_avoided(kg)

    impact_stmt = select(ImpactLog).where(ImpactLog.donation_id == donation.id)
    impact_row = (await db.execute(impact_stmt)).scalar_one_or_none()
    if not impact_row:
        impact_row = ImpactLog(
            id=uuid.uuid4(),
            donation_id=donation.id,
            kg_rescued=kg,
            meals_equivalent=meals,
            co2e_avoided_kg=co2e,
            method_version="v1.0",
        )
        db.add(impact_row)
    else:
        impact_row.kg_rescued = kg
        impact_row.meals_equivalent = meals
        impact_row.co2e_avoided_kg = co2e

    await db.commit()
    await db.refresh(impact_row)

    # Notify donor of successful rescue
    if donation.donor and donation.donor.user:
        await notification_service.notify_pickup_completed(
            db=db,
            donor_user_id=donation.donor.user.id,
            donation_id=donation.id,
            claim_id=claim.id,
            kg_rescued=kg,
            meals_equivalent=meals,
        )

    response_data = _build_claim_read(claim, impact_record=impact_row)
    await ws_manager.broadcast("donation_completed", response_data.model_dump(mode="json"))

    return response_data


@router.post(
    "/{claim_id}/accept",
    summary="Accept an offered food rescue claim",
    response_model=ClaimRead,
)
async def accept_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimRead:
    """Recipient accepts an offered food rescue claim, locking the match."""
    stmt = (
        select(Claim)
        .options(
            selectinload(Claim.donation).selectinload(Donation.donor).selectinload(Donor.user),
            selectinload(Claim.donation).selectinload(Donation.impact_log),
            selectinload(Claim.recipient).selectinload(Recipient.user),
        )
        .where(Claim.id == claim_id)
    )
    claim = (await db.execute(stmt)).scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found.",
        )

    if claim.status == ClaimStatus.accepted:
        return _build_claim_read(claim)

    if claim.status != ClaimStatus.offered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Claim in '{claim.status.value}' status cannot be accepted.",
        )

    now = datetime.now(UTC)
    claim.status = ClaimStatus.accepted
    claim.responded_at = now

    if claim.donation:
        claim.donation.status = DonationStatus.matched

    await db.commit()
    await db.refresh(claim)

    # Notify donor via push notification
    if claim.donation and claim.donation.donor and claim.donation.donor.user:
        recipient_display = (
            current_user.display_name or current_user.org_name or "A verified food rescue partner"
        )
        await notification_service.notify_donation_claimed(
            db=db,
            donor_user_id=claim.donation.donor.user.id,
            donation_id=claim.donation.id,
            claim_id=claim.id,
            recipient_name=recipient_display,
            item_name=claim.donation.item.value,
        )

    response_data = _build_claim_read(claim)
    await ws_manager.broadcast("donation_matched", response_data.model_dump(mode="json"))

    return response_data
