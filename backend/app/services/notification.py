"""BountyLoop — Push Notification Service (FCM).

Provides device token registration and push notification dispatch via Firebase Admin SDK
with graceful offline/mock fallback for test and local development (§6 Phase 6).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Test/in-memory dispatch log for verifying assertions in tests
DISPATCHED_NOTIFICATIONS: list[dict[str, Any]] = []


class NotificationService:
    """Manages FCM device tokens and push notification delivery."""

    async def register_device(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        fcm_token: str,
        platform: str = "android",
    ) -> Device:
        """Register or update an FCM token for a user."""
        stmt = select(Device).where(Device.fcm_token == fcm_token)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()

        if device:
            device.user_id = user_id
            device.platform = platform
        else:
            device = Device(
                id=uuid.uuid4(),
                user_id=user_id,
                fcm_token=fcm_token,
                platform=platform,
            )
            db.add(device)

        await db.commit()
        await db.refresh(device)
        logger.info("Registered device %s for user %s on %s", device.id, user_id, platform)
        return device

    async def get_user_device_tokens(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[str]:
        """Fetch all registered FCM tokens for a user."""
        stmt = select(Device.fcm_token).where(Device.user_id == user_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def send_push(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> int:
        """Deliver push notification to all active devices of a user.

        Attempts Firebase Admin Messaging delivery; falls back safely to logging and in-memory store.
        """
        tokens = await self.get_user_device_tokens(db, user_id)
        payload_data = data or {}

        record = {
            "user_id": str(user_id),
            "tokens": tokens,
            "title": title,
            "body": body,
            "data": payload_data,
        }
        DISPATCHED_NOTIFICATIONS.append(record)

        # Broadcast via WebSocket so web and mobile clients receive real-time push
        await ws_manager.broadcast(
            "notification",
            {
                "user_id": str(user_id),
                "title": title,
                "body": body,
                "data": payload_data,
            },
        )

        if not tokens:
            logger.info("User %s has no registered devices; logged push: %s", user_id, title)
            return 0

        try:
            # Try Firebase Admin messaging if available
            import firebase_admin
            from firebase_admin import messaging

            if firebase_admin._apps:
                messages = [
                    messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data={k: str(v) for k, v in payload_data.items()},
                        token=tok,
                    )
                    for tok in tokens
                ]
                response = messaging.send_each(messages)
                logger.info(
                    "FCM dispatched to user %s (%d successful, %d failed)",
                    user_id,
                    response.success_count,
                    response.failure_count,
                )
                return response.success_count
        except Exception as err:
            logger.warning("FCM delivery gracefully degraded to mock dispatch: %s", err)

        return len(tokens)

    async def notify_donation_claimed(
        self,
        db: AsyncSession,
        donor_user_id: uuid.UUID,
        donation_id: uuid.UUID,
        claim_id: uuid.UUID,
        recipient_name: str,
        item_name: str,
    ) -> None:
        """Notify donor that their donation was claimed by a recipient."""
        await self.send_push(
            db=db,
            user_id=donor_user_id,
            title="Donation Matched! 🎉",
            body=f"{recipient_name} has claimed your donation of {item_name}.",
            data={
                "type": "donation_matched",
                "donation_id": str(donation_id),
                "claim_id": str(claim_id),
            },
        )

    async def notify_pickup_completed(
        self,
        db: AsyncSession,
        donor_user_id: uuid.UUID,
        donation_id: uuid.UUID,
        claim_id: uuid.UUID,
        kg_rescued: float,
        meals_equivalent: float,
    ) -> None:
        """Notify donor that pickup is complete and impact was achieved."""
        await self.send_push(
            db=db,
            user_id=donor_user_id,
            title="Pickup Completed! 💚",
            body=f"Your donation was rescued ({kg_rescued:.1f} kg, ~{meals_equivalent:.0f} meals provided). Thank you!",
            data={
                "type": "pickup_completed",
                "donation_id": str(donation_id),
                "claim_id": str(claim_id),
                "kg_rescued": f"{kg_rescued:.2f}",
                "meals": f"{meals_equivalent:.1f}",
            },
        )


notification_service = NotificationService()
