"""BountyLoop — Device Registration Endpoints (FCM).

Handles registration and updating of FCM tokens for mobile and web push notifications (§6 Phase 6).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.claim import DeviceRegister
from app.services.notification import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Register or update device FCM token",
)
async def register_device(
    payload: DeviceRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Register or update an FCM token for push notifications."""
    await notification_service.register_device(
        db=db,
        user_id=current_user.id,
        fcm_token=payload.fcm_token,
        platform=payload.platform,
    )

