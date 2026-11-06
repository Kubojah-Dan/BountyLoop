"""BountyLoop — Communication Dispatch Bus.

Orchestrates multi-channel notifications (Push / FCM, SMS / Twilio fallback, WebSocket).
Enforces push-first delivery to preserve SMS budget (SMS_DAILY_CAP = 20) while ensuring
high reliability for urgent food rescue notifications (§6 Phase 9).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.claim import Claim
from app.db.models.donation import Donation
from app.db.models.recipient import Recipient
from app.db.models.user import User
from app.services.notification import notification_service
from app.services.sms import SmsSendResult, twilio_sms_client
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Test/audit dispatch log
COMMUNICATION_DISPATCH_LOG: list[dict[str, Any]] = []


@dataclass
class CommunicationReceipt:
    """Delivery receipt tracking channels used and outcome."""

    user_id: uuid.UUID
    primary_channel: str  # "push", "sms", "websocket_only"
    push_delivered: bool
    push_device_count: int
    sms_dispatched: bool
    sms_result: SmsSendResult | None
    websocket_broadcast: bool
    timestamp: datetime


class CommunicationBus:
    """Unified communications router enforcing push-first delivery and SMS fallback."""

    def __init__(self) -> None:
        self.notification_svc = notification_service
        self.sms_client = twilio_sms_client

    async def dispatch_notification(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        body: str,
        sms_body: str | None = None,
        data: dict[str, str] | None = None,
        force_channel: str | None = None,
        claim_id: uuid.UUID | None = None,
    ) -> CommunicationReceipt:
        """Deliver an alert following the push-first policy.

        1. Always broadcast via WebSocket for real-time dashboards & connected apps.
        2. If force_channel == 'sms': immediately attempt SMS.
        3. Otherwise, check for registered FCM device tokens:
           - If active tokens exist: deliver via Push (FCM). Zero SMS cost.
           - If no device tokens exist or push fails: fall back to SMS (subject to daily cap).
        4. If user has no phone number, record delivery as 'websocket_only'.
        """
        payload_data = data or {}
        now = datetime.now(UTC)

        # 1. Real-time WebSocket Broadcast
        await ws_manager.broadcast(
            "communication_alert",
            {
                "user_id": str(user_id),
                "title": title,
                "body": body,
                "data": payload_data,
                "claim_id": str(claim_id) if claim_id else None,
                "timestamp": now.isoformat(),
            },
        )

        # Load user to inspect phone_e164
        u_stmt = select(User).where(User.id == user_id)
        u_res = await db.execute(u_stmt)
        user = u_res.scalar_one_or_none()
        user_phone = user.phone_e164 if user else None

        push_delivered = False
        push_count = 0
        sms_dispatched = False
        sms_res: SmsSendResult | None = None
        primary_channel = "websocket_only"

        # 2. Push-First Attempt
        if force_channel != "sms":
            device_tokens = await self.notification_svc.get_user_device_tokens(db, user_id)
            if device_tokens:
                push_count = await self.notification_svc.send_push(
                    db=db,
                    user_id=user_id,
                    title=title,
                    body=body,
                    data=payload_data,
                )
                if push_count > 0:
                    push_delivered = True
                    primary_channel = "push"
                    logger.info(
                        "Push-first delivery successful for user %s (%d devices). SMS suppressed.",
                        user_id,
                        push_count,
                    )

        # 3. SMS Fallback Attempt
        # Triggered when:
        # a) forced via force_channel == 'sms', or
        # b) user has no registered push devices, or
        # c) push attempt failed to reach any devices.
        if (force_channel == "sms" or not push_delivered) and user_phone:
            actual_sms_text = sms_body or f"{title}: {body}"
            logger.info(
                "Falling back to SMS for user %s (%s) — push_delivered=%s",
                user_id,
                user_phone,
                push_delivered,
            )
            sms_res = await self.sms_client.send_sms(
                to_phone=user_phone,
                body=actual_sms_text,
                user_id=user_id,
                claim_id=claim_id,
                db=db,
            )
            sms_dispatched = sms_res.success
            primary_channel = "sms"

        receipt = CommunicationReceipt(
            user_id=user_id,
            primary_channel=primary_channel,
            push_delivered=push_delivered,
            push_device_count=push_count,
            sms_dispatched=sms_dispatched,
            sms_result=sms_res,
            websocket_broadcast=True,
            timestamp=now,
        )

        COMMUNICATION_DISPATCH_LOG.append(
            {
                "user_id": str(user_id),
                "primary_channel": primary_channel,
                "push_delivered": push_delivered,
                "sms_dispatched": sms_dispatched,
                "sms_status": sms_res.status if sms_res else None,
                "title": title,
                "timestamp": now.isoformat(),
            }
        )

        return receipt

    async def dispatch_claim_offer(
        self,
        db: AsyncSession,
        recipient: Recipient,
        donation: Donation,
        claim: Claim,
    ) -> CommunicationReceipt:
        """Notify a recipient organization of a pending surplus donation offer."""
        recipient_user_id = recipient.user_id
        item_name = donation.item.value
        weight_kg = float(donation.weight_kg)
        claim_code = claim.id.hex[:8].upper()

        push_title = "New Food Rescue Offer! 🥗"
        push_body = (
            f"{weight_kg:.1f}kg of {item_name} is available near you. Tap to review and accept!"
        )
        sms_text = (
            f"BountyLoop Offer: {weight_kg:.1f}kg of {item_name} available. "
            f"Reply RESCUE {claim_code} to accept or DECLINE {claim_code} to pass. "
            f"Offer expires in 30 mins."
        )

        return await self.dispatch_notification(
            db=db,
            user_id=recipient_user_id,
            title=push_title,
            body=push_body,
            sms_body=sms_text,
            data={
                "type": "claim_offer",
                "donation_id": str(donation.id),
                "claim_id": str(claim.id),
                "claim_code": claim_code,
                "weight_kg": f"{weight_kg:.2f}",
                "item": item_name,
            },
            claim_id=claim.id,
        )

    async def dispatch_claim_accepted(
        self,
        db: AsyncSession,
        donor_user_id: uuid.UUID,
        recipient: Recipient,
        donation: Donation,
        claim: Claim,
    ) -> CommunicationReceipt:
        """Notify donor that their surplus donation has been accepted for rescue."""
        # Ensure recipient user is loaded
        recipient_stmt = (
            select(Recipient)
            .options(selectinload(Recipient.user))
            .where(Recipient.id == recipient.id)
        )
        rec_res = await db.execute(recipient_stmt)
        rec_loaded = rec_res.scalar_one_or_none() or recipient

        recipient_name = (
            rec_loaded.user.org_name
            or rec_loaded.user.display_name
            or "Verified Food Rescue Partner"
            if rec_loaded.user
            else "Verified Food Rescue Partner"
        )
        item_name = donation.item.value
        weight_kg = float(donation.weight_kg)

        push_title = "Donation Matched! 🎉"
        push_body = f"{recipient_name} has accepted your donation of {weight_kg:.1f}kg of {item_name}. Pickup is in progress!"
        sms_text = (
            f"BountyLoop: {recipient_name} has accepted your donation of {weight_kg:.1f}kg {item_name}. "
            f"They are en route for pickup. Thank you for rescuing food!"
        )

        return await self.dispatch_notification(
            db=db,
            user_id=donor_user_id,
            title=push_title,
            body=push_body,
            sms_body=sms_text,
            data={
                "type": "donation_matched",
                "donation_id": str(donation.id),
                "claim_id": str(claim.id),
                "recipient_name": recipient_name,
                "item": item_name,
            },
            claim_id=claim.id,
        )

    async def dispatch_pickup_reminder(
        self,
        db: AsyncSession,
        recipient: Recipient,
        donation: Donation,
        claim: Claim,
    ) -> CommunicationReceipt:
        """Send pickup reminder to recipient."""
        recipient_user_id = recipient.user_id
        item_name = donation.item.value
        claim_code = claim.id.hex[:8].upper()

        push_title = "Pickup Reminder ⏰"
        push_body = f"Pickup pending for {item_name} at {donation.pickup_address}."
        sms_text = (
            f"BountyLoop Reminder: Pickup for {item_name} at {donation.pickup_address}. "
            f"Claim ref #{claim_code}. Reply STATUS for claim summary."
        )

        return await self.dispatch_notification(
            db=db,
            user_id=recipient_user_id,
            title=push_title,
            body=push_body,
            sms_body=sms_text,
            data={
                "type": "pickup_reminder",
                "donation_id": str(donation.id),
                "claim_id": str(claim.id),
                "pickup_address": donation.pickup_address,
            },
            claim_id=claim.id,
        )


communication_bus = CommunicationBus()
