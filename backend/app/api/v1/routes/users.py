"""BountyLoop — User Profile and Role Management Endpoints.

Handles /me profile reading, updates, onboarding role assignment,
and role-guarded resource access.
"""

from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_role
from app.db.base import utc_now
from app.db.models import Donor, User, UserRole
from app.db.session import get_db
from app.schemas.user import RoleUpdateRequest, UserPurgeResponse, UserRead, UserUpdate
from app.services.storage import PHOTOS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated Firebase user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Return the profile of the authenticated user."""
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Update display name, phone number, or organization name.",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Update profile fields for the authenticated user."""
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.phone_e164 is not None:
        current_user.phone_e164 = payload.phone_e164
    if payload.org_name is not None:
        current_user.org_name = payload.org_name
    if payload.consent_model_training is not None:
        current_user.consent_model_training = payload.consent_model_training

    current_user.last_seen_at = utc_now()
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.delete(
    "/me/data",
    response_model=UserPurgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Purge personal data and photos (Right to be Forgotten)",
    description=(
        "Permanently wipes uploaded photos from disk, clears retraining consent, "
        "and anonymizes personal information in compliance with retention schedule."
    ),
)
async def purge_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPurgeResponse:
    """Purge user PII, donation photos, and labels."""
    photos_deleted_count = 0

    # 1. Locate all donations associated with user's donor profile
    donor_stmt = (
        select(Donor).options(selectinload(Donor.donations)).where(Donor.user_id == current_user.id)
    )
    donor_res = await db.execute(donor_stmt)
    donor = donor_res.scalar_one_or_none()

    if donor and donor.donations:
        for don in donor.donations:
            # Delete donation photo directory on disk
            donation_dir = PHOTOS_DIR / str(don.id)
            if donation_dir.exists():
                try:
                    num_files = len(list(donation_dir.glob("*")))
                    shutil.rmtree(donation_dir)
                    photos_deleted_count += num_files
                except Exception as exc:
                    logger.warning("Failed to delete photo directory %s: %s", donation_dir, exc)
            don.photo_paths = []

    # 2. Anonymize user profile
    current_user.display_name = "Deleted User"
    current_user.email = f"purged_{current_user.id.hex[:12]}@privacy.bountyloop.local"
    current_user.phone_e164 = None
    current_user.org_name = None
    current_user.is_active = False
    current_user.consent_model_training = False
    current_user.last_seen_at = utc_now()

    await db.commit()
    logger.info(
        "Purged PII and %d photos for user %s (Right to be Forgotten)",
        photos_deleted_count,
        current_user.id,
    )

    return UserPurgeResponse(
        status="purged",
        message="User personal data and associated media have been permanently purged.",
        user_id=current_user.id,
        photos_deleted=photos_deleted_count,
        retention_policy_link="/docs/privacy.md",
        purged_at=utc_now(),
    )


@router.post(
    "/me/role",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Set or update role during onboarding",
    description="Contract endpoint: POST /v1/me/role {role, org_name?} -> profile.",
)
async def update_my_role(
    payload: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Set role and organization name during user onboarding."""
    current_user.role = payload.role
    if payload.org_name is not None:
        current_user.org_name = payload.org_name

    current_user.last_seen_at = utc_now()
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)


# ── Role-Guarded Demonstration Routes ─────────────────────────────────────────


@router.get(
    "/role-guard/recipient-only",
    status_code=status.HTTP_200_OK,
    summary="Recipient-only protected route",
    description="Demonstrates role guard restricting access strictly to recipient accounts.",
)
async def recipient_only_route(
    current_user: User = Depends(require_role(UserRole.recipient)),
) -> dict[str, str]:
    """Test endpoint accessible only to recipient users."""
    return {"message": f"Welcome recipient {current_user.display_name}"}


@router.get(
    "/role-guard/donor-only",
    status_code=status.HTTP_200_OK,
    summary="Donor-only protected route",
    description="Demonstrates role guard restricting access strictly to donor accounts.",
)
async def donor_only_route(
    current_user: User = Depends(require_role(UserRole.donor)),
) -> dict[str, str]:
    """Test endpoint accessible only to donor users."""
    return {"message": f"Welcome donor {current_user.display_name}"}


@router.get(
    "/role-guard/admin-only",
    status_code=status.HTTP_200_OK,
    summary="Admin-only protected route",
    description="Demonstrates role guard restricting access strictly to admin accounts.",
)
async def admin_only_route(
    current_user: User = Depends(require_role(UserRole.admin)),
) -> dict[str, str]:
    """Test endpoint accessible only to administrator users."""
    return {"message": f"Welcome admin {current_user.display_name}"}
