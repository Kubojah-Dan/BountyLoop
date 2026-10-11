"""BountyLoop — User Profile and Role Management Endpoints.

Handles /me profile reading, updates, onboarding role assignment,
and role-guarded resource access.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.base import utc_now
from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas.user import RoleUpdateRequest, UserRead, UserUpdate

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

    current_user.last_seen_at = utc_now()
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)


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
