"""BountyLoop — Donation Management API Endpoints.

Implements the complete Photo-to-Donate flow (§6 Phase 5):
- POST /v1/donations: Upload 1-3 photos, server-side EXIF stripping, CV classification, draft donation creation
- PATCH /v1/donations/{id}/confirm: Donor confirmation/correction, recomputing expiry, appending to retraining label store
- GET /v1/donations: Paginated donation feed with filters
- GET /v1/donations/{id}: Detail view
- DELETE /v1/donations/{id}: Soft-cancellation (only when draft or open)
- GET /v1/donations/{id}/photos/{idx}: Authenticated photo serving
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.models import (
    Donation,
    DonationStatus,
    Donor,
    DonorKind,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    ReviewQueue,
    ReviewReason,
    ReviewStatus,
    User,
    UserRole,
)
from app.db.session import get_db
from app.schemas.donation import DonationConfirm, DonationRead
from app.services.cv_client import cv_client
from app.services.freshness_rules import calculate_expiry
from app.services.label_store import append_label_record
from app.services.storage import read_photo_bytes, save_donation_photo
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/donations", tags=["donations"])

# In-memory recent photo hash cache for immediate duplicate detection: hash -> (donor_id, timestamp)
_recent_photo_hashes: dict[str, tuple[uuid.UUID, datetime]] = {}


def _check_and_register_photo_hash(photo_hash: str, donor_id: uuid.UUID) -> None:
    """Check if the exact same photo hash was uploaded recently by this donor."""
    now = datetime.now(UTC)
    # Evict hashes older than 1 hour
    expired = [h for h, (_, ts) in _recent_photo_hashes.items() if now - ts > timedelta(hours=1)]
    for h in expired:
        _recent_photo_hashes.pop(h, None)

    if photo_hash in _recent_photo_hashes:
        cached_donor_id, ts = _recent_photo_hashes[photo_hash]
        if cached_donor_id == donor_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate photo detected. A donation with this photo was already submitted recently.",
            )

    _recent_photo_hashes[photo_hash] = (donor_id, now)


async def _resolve_or_create_donor(
    user: User,
    db: AsyncSession,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
) -> Donor:
    """Retrieve donor profile for user, or provision one if this is their first donation."""
    stmt = select(Donor).where(Donor.user_id == user.id)
    result = await db.execute(stmt)
    donor = result.scalar_one_or_none()

    if donor:
        return donor

    # Reject if user is explicitly a recipient organization
    if user.role == UserRole.recipient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users registered as recipients cannot create food donations.",
        )

    # Auto-provision a donor profile for the user
    lat = latitude if latitude is not None else 30.2672
    lon = longitude if longitude is not None else -97.7431
    addr = address or user.org_name or "Austin, TX"

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.household if user.role == UserRole.donor else DonorKind.other,
        address=addr,
        location=WKTElement(f"POINT({lon} {lat})", srid=4326),
        timezone="America/Chicago",
        avg_surplus_schedule=None,
    )
    db.add(donor)
    await db.flush()
    logger.info("Auto-provisioned Donor profile %s for user %s", donor.id, user.id)
    return donor


def _build_donation_read(donation: Donation) -> DonationRead:
    """Map DB entity to Pydantic response schema with enriched donor fields."""
    donor_name = None
    donor_address = None
    if donation.donor:
        donor_address = donation.donor.address
        if donation.donor.user:
            donor_name = donation.donor.user.display_name or donation.donor.user.org_name

    return DonationRead(
        id=donation.id,
        donor_id=donation.donor_id,
        photo_paths=list(donation.photo_paths or []),
        item=donation.item,
        item_confidence=float(donation.item_confidence),
        freshness=donation.freshness,
        freshness_confidence=float(donation.freshness_confidence),
        hazard_flag=donation.hazard_flag,
        est_weight_kg=float(donation.est_weight_kg),
        expires_at=donation.expires_at,
        status=donation.status,
        needs_review=donation.needs_review,
        model_versions=donation.model_versions,
        created_at=donation.created_at,
        donor_name=donor_name,
        donor_address=donor_address,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create donation from photo(s)",
    response_model=DonationRead,
)
async def create_donation(
    files: Annotated[list[UploadFile], File(description="1 to 3 food photos")],
    est_weight_kg: Annotated[float | None, Form(ge=0.1, le=5000.0)] = None,
    latitude: Annotated[float | None, Form(ge=-90.0, le=90.0)] = None,
    longitude: Annotated[float | None, Form(ge=-180.0, le=180.0)] = None,
    address: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DonationRead:
    """Photo-to-Donate ingestion endpoint.

    Performs:
    1. Validation of image count (1-3) and total size (<10MB).
    2. Server-side EXIF stripping and SHA-256 deduplication.
    3. CV inference via cv_client (with graceful offline fallback).
    4. Draft donation creation + review queue triage if low confidence or hazard detected.
    5. WebSocket broadcast for real-time dashboards.
    """
    if not files or len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one food photo is required to create a donation.",
        )
    if len(files) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 3 photos allowed per donation.",
        )

    # 1. Resolve donor profile
    donor = await _resolve_or_create_donor(
        user=current_user,
        db=db,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )

    donation_id = uuid.uuid4()
    saved_photo_paths: list[str] = []
    primary_photo_bytes: bytes | None = None
    max_upload_bytes = settings.max_upload_mb * 1024 * 1024

    # 2. Process, sanitize, and save each uploaded photo
    for idx, uploaded_file in enumerate(files):
        content = await uploaded_file.read()
        if not content or len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Photo '{uploaded_file.filename}' is empty.",
            )
        if len(content) > max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Photo '{uploaded_file.filename}' exceeds the maximum size of {settings.max_upload_mb} MB.",
            )

        # Sanitize EXIF, hash, and persist to storage/photos/<donation_id>/<uuid>.jpg
        rel_path, photo_hash = save_donation_photo(donation_id, content)

        # Check deduplication on the primary (first) photo
        if idx == 0:
            _check_and_register_photo_hash(photo_hash, donor.id)
            primary_photo_bytes = content

        saved_photo_paths.append(rel_path)

    # 3. Execute CV Inference on the primary photo
    cv_result = await cv_client.predict(
        image_bytes=primary_photo_bytes,
        filename=files[0].filename or "food.jpg",
        content_type=files[0].content_type or "image/jpeg",
        apply_tta=settings.tta,
    )

    item: FoodCategory = cv_result["item"]
    freshness: FreshnessGrade = cv_result["freshness"]
    hazard_flag: HazardFlag = cv_result["hazard_flag"]
    needs_review: bool = cv_result["needs_review"]
    review_reason_str = cv_result.get("review_reason")

    # Flag review if food is spoiled or suspected hazard
    is_spoiled = freshness in (FreshnessGrade.spoiled, FreshnessGrade.grade_0_spoiled)
    has_hazard = hazard_flag != HazardFlag.none
    if is_spoiled or has_hazard:
        needs_review = True
        review_reason_str = "hazard"

    # Compute shelf-life expiry
    expires_at = calculate_expiry(item, freshness)
    weight_kg = est_weight_kg if est_weight_kg is not None else 2.50

    # 4. Create and persist Donation row (draft status)
    donation = Donation(
        id=donation_id,
        donor_id=donor.id,
        photo_paths=saved_photo_paths,
        item=item,
        item_confidence=cv_result["item_confidence"],
        freshness=freshness,
        freshness_confidence=cv_result["freshness_confidence"],
        hazard_flag=hazard_flag,
        est_weight_kg=weight_kg,
        expires_at=expires_at,
        status=DonationStatus.draft,
        needs_review=needs_review,
        model_versions=cv_result.get("model_versions"),
    )
    db.add(donation)

    # 5. Automatically create ReviewQueue entry if human triage is needed
    if needs_review:
        review_reason = (
            ReviewReason.hazard if review_reason_str == "hazard" else ReviewReason.low_confidence
        )
        review_item = ReviewQueue(
            id=uuid.uuid4(),
            donation_id=donation.id,
            reason=review_reason,
            status=ReviewStatus.pending,
            note=f"Triage required: {review_reason_str or 'confidence_threshold'}",
        )
        db.add(review_item)

    await db.commit()
    await db.refresh(donation, attribute_names=["donor"])

    response_data = _build_donation_read(donation)

    # 6. Broadcast event over WebSocket
    await ws_manager.broadcast("donation_created", response_data.model_dump(mode="json"))

    return response_data


@router.patch(
    "/{donation_id}/confirm",
    summary="Confirm or correct donation classification",
    response_model=DonationRead,
)
async def confirm_donation(
    donation_id: uuid.UUID,
    payload: DonationConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DonationRead:
    """Donor confirmation/correction endpoint.

    Transitions donation from 'draft' to 'open', re-computes shelf-life expiry,
    and logs corrections to the active learning label store.
    """
    stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == donation_id)
    )
    result = await db.execute(stmt)
    donation = result.scalar_one_or_none()

    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation '{donation_id}' not found.",
        )

    # Ensure caller is the donor or an admin
    if donation.donor.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this donation.",
        )

    if donation.status != DonationStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot confirm donation with status '{donation.status.value}'. Must be 'draft'.",
        )

    initial_item = donation.item.value
    initial_freshness = donation.freshness.value

    # Apply donor corrections
    if payload.item is not None:
        donation.item = payload.item
    if payload.freshness is not None:
        donation.freshness = payload.freshness
    if payload.est_weight_kg is not None:
        donation.est_weight_kg = payload.est_weight_kg

    # Recompute expiry timestamp with confirmed category & grade
    donation.expires_at = calculate_expiry(
        donation.item, donation.freshness, base_time=donation.created_at
    )

    # Transition status: if hazard/spoiled, remain in needs_review but mark status as open
    donation.status = DonationStatus.open

    # Log to retraining label store (§5.7)
    primary_photo = donation.photo_paths[0] if donation.photo_paths else "photos/unknown.jpg"
    append_label_record(
        donation_id=str(donation.id),
        donor_id=str(donation.donor_id),
        photo_path=primary_photo,
        initial_item=initial_item,
        initial_freshness=initial_freshness,
        confirmed_item=donation.item.value,
        confirmed_freshness=donation.freshness.value,
        confirmed_weight_kg=float(donation.est_weight_kg),
    )

    await db.commit()
    await db.refresh(donation, attribute_names=["donor"])

    response_data = _build_donation_read(donation)
    await ws_manager.broadcast("donation_confirmed", response_data.model_dump(mode="json"))

    return response_data


@router.get(
    "",
    summary="List donations",
    response_model=dict,
)
async def list_donations(
    status_filter: Annotated[DonationStatus | None, Query(alias="status")] = None,
    mine: Annotated[bool, Query(description="Filter to current user's donations")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List donations with optional status and ownership filters."""
    query = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .order_by(Donation.created_at.desc())
    )
    count_query = select(func.count()).select_from(Donation)

    if status_filter:
        query = query.where(Donation.status == status_filter)
        count_query = count_query.where(Donation.status == status_filter)

    if mine:
        # Join donor to filter by user_id
        query = query.join(Donor).where(Donor.user_id == current_user.id)
        count_query = count_query.join(Donor).where(Donor.user_id == current_user.id)

    total_count = (await db.execute(count_query)).scalar() or 0
    items_result = await db.execute(query.limit(limit).offset(offset))
    donations = items_result.scalars().all()

    items = [_build_donation_read(d) for d in donations]
    return {
        "items": items,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{donation_id}",
    summary="Get donation by ID",
    response_model=DonationRead,
)
async def get_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DonationRead:
    """Retrieve full detail of a specific donation."""
    stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == donation_id)
    )
    result = await db.execute(stmt)
    donation = result.scalar_one_or_none()

    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation '{donation_id}' not found.",
        )

    return _build_donation_read(donation)


@router.delete(
    "/{donation_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel donation",
    response_model=DonationRead,
)
async def cancel_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DonationRead:
    """Soft-cancel a donation. Allowed only while status is draft or open."""
    stmt = (
        select(Donation)
        .options(selectinload(Donation.donor).selectinload(Donor.user))
        .where(Donation.id == donation_id)
    )
    result = await db.execute(stmt)
    donation = result.scalar_one_or_none()

    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation '{donation_id}' not found.",
        )

    # Check permission
    if donation.donor.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this donation.",
        )

    if donation.status not in (DonationStatus.draft, DonationStatus.open):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel donation in '{donation.status.value}' state. Must be draft or open.",
        )

    donation.status = DonationStatus.cancelled
    await db.commit()
    await db.refresh(donation, attribute_names=["donor"])

    response_data = _build_donation_read(donation)
    await ws_manager.broadcast("donation_cancelled", response_data.model_dump(mode="json"))
    return response_data


@router.get(
    "/{donation_id}/photos/{photo_index}",
    summary="Get authenticated donation photo",
    response_class=Response,
)
async def get_donation_photo(
    donation_id: uuid.UUID,
    photo_index: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Stream sanitized photo bytes securely."""
    stmt = select(Donation).where(Donation.id == donation_id)
    result = await db.execute(stmt)
    donation = result.scalar_one_or_none()

    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation '{donation_id}' not found.",
        )

    if photo_index < 0 or photo_index >= len(donation.photo_paths):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo index {photo_index} out of range.",
        )

    rel_path = donation.photo_paths[photo_index]
    photo_bytes = read_photo_bytes(rel_path)
    return Response(content=photo_bytes, media_type="image/jpeg")
