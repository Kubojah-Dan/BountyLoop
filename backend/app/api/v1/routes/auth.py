"""BountyLoop — Authentication and Session API Endpoints.

Handles Firebase ID token verification, session initiation, and role selection.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, verify_firebase_token
from app.db.base import utc_now
from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas.user import RoleUpdateRequest, SessionCreate, SessionResponse, UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/session",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or resume session via Firebase ID token",
    description="Verifies the provided Firebase Auth ID token and returns internal user profile and role.",
)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Verify Firebase ID token and return session data with upserted user profile."""
    claims = verify_firebase_token(payload.id_token)
    firebase_uid = claims["uid"]
    email = claims.get("email") or f"{firebase_uid}@bountyloop.local"
    display_name = claims.get("name") or email.split("@")[0]

    # Query or upsert user
    user = (
        await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    ).scalar_one_or_none()

    if user is None:
        # Check by email as fallback
        existing_email_user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing_email_user is not None:
            user = existing_email_user
            user.firebase_uid = firebase_uid
            user.last_seen_at = utc_now()
        else:
            user = User(
                firebase_uid=firebase_uid,
                role=UserRole.donor,
                display_name=display_name,
                email=email,
                is_active=True,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)
    else:
        user.last_seen_at = utc_now()
        await db.commit()

    return SessionResponse(
        user_id=user.id,
        role=user.role,
        profile=UserRead.model_validate(user),
    )


@router.post(
    "/role",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update or set user role at onboarding (auth alias)",
)
async def update_auth_role(
    payload: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Set or switch user role during onboarding flow."""
    current_user.role = payload.role
    if payload.org_name is not None:
        current_user.org_name = payload.org_name
    current_user.last_seen_at = utc_now()
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)
