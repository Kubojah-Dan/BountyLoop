"""BountyLoop — Twilio SMS Webhook & Quota Routes.

Provides endpoints for inbound SMS webhooks (one-tap RESCUE/ACCEPT claim confirmation),
daily SMS usage monitoring, and outbound manual dispatch (§6 Phase 9).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, Header, Request, Response
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import String

from app.db.models.claim import Claim
from app.db.models.donation import Donation
from app.db.models.donor import Donor
from app.db.models.enums import ClaimStatus, DonationStatus
from app.db.models.sms_message import SmsMessage
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.sms import (
    InboundWebhookResponse,
    SmsSendRequest,
    SmsSendResponse,
    SmsUsageRead,
)
from app.services.communication import communication_bus
from app.services.sms import twilio_sms_client
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sms", tags=["SMS & Communications"])


def _clean_phone(raw_phone: str) -> str:
    """Normalize phone number to standard E.164 digits with leading +."""
    digits_only = re.sub(r"[^\d+]", "", raw_phone.strip())
    if not digits_only.startswith("+") and digits_only:
        digits_only = f"+{digits_only}"
    return digits_only


def _format_twiml(message_text: str) -> str:
    """Generate standard TwiML XML response for Twilio webhook."""
    escaped = (
        message_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Message>{escaped}</Message>\n</Response>'


@router.get("/usage", response_model=SmsUsageRead, summary="Current daily SMS dispatch quota usage")
async def get_sms_usage(db: AsyncSession = Depends(get_db)) -> SmsUsageRead:
    """Return the volume of SMS messages dispatched today, the hard cap (20), and remaining quota."""
    usage = await twilio_sms_client.get_daily_usage(db)
    return SmsUsageRead(
        date=usage.date,
        sent_today=usage.sent_today,
        daily_cap=usage.daily_cap,
        remaining=usage.remaining,
        is_capped=usage.is_capped,
    )


@router.post(
    "/send", response_model=SmsSendResponse, summary="Send manual SMS (subject to daily cap)"
)
async def send_manual_sms(
    payload: SmsSendRequest,
    db: AsyncSession = Depends(get_db),
) -> SmsSendResponse:
    """Send an outbound SMS alert, enforcing the hard SMS_DAILY_CAP = 20."""
    result = await twilio_sms_client.send_sms(
        to_phone=payload.to_phone,
        body=payload.body,
        user_id=payload.user_id,
        claim_id=payload.claim_id,
        db=db,
    )
    return SmsSendResponse(
        success=result.success,
        status=result.status,
        to_phone=result.to_phone,
        body=result.body,
        daily_count=result.daily_count,
        daily_cap=result.daily_cap,
        message_sid=result.message_sid,
        error=result.error,
    )


@router.post(
    "/webhook",
    summary="Twilio inbound SMS webhook handler",
    response_description="TwiML XML response or JSON",
)
async def twilio_inbound_webhook(
    request: Request,
    from_phone: str | None = Form(None, alias="From"),
    to_phone: str | None = Form(None, alias="To"),
    body_text: str | None = Form(None, alias="Body"),
    message_sid: str | None = Form(None, alias="MessageSid"),
    accept: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Handle incoming SMS messages from Twilio.

    Supports one-tap claim confirmation:
    - `RESCUE <claim_id_or_prefix>`: accept offer and trigger donor notification
    - `ACCEPT <claim_id_or_prefix>`: alias for RESCUE
    - `DECLINE <claim_id_or_prefix>`: decline claim offer
    - `STATUS`: check active offers / claims
    - `HELP`: list available SMS commands
    """
    # 1. Fallback parse for JSON payloads (common in unit tests and webhooks)
    if from_phone is None:
        try:
            body_json = await request.json()
            if isinstance(body_json, dict):
                from_phone = body_json.get("From") or body_json.get("from")
                to_phone = body_json.get("To") or body_json.get("to")
                body_text = body_json.get("Body") or body_json.get("body")
                message_sid = body_json.get("MessageSid") or body_json.get("message_sid")
        except Exception:
            pass

    sender_phone = _clean_phone(from_phone or "")
    twilio_number = (to_phone or "").strip()
    raw_body = (body_text or "").strip()
    sid = message_sid or f"SM_in_{uuid.uuid4().hex[:24]}"

    logger.info("Inbound SMS received from %s (SID: %s): %s", sender_phone, sid, raw_body)

    # 2. Record incoming message in audit log
    inbound_log = SmsMessage(
        id=uuid.uuid4(),
        direction="inbound",
        to_phone=twilio_number or "+10000000000",
        from_phone=sender_phone or "unknown",
        body=raw_body,
        status="received",
        sid=sid,
    )
    db.add(inbound_log)

    tokens = raw_body.split()
    command = tokens[0].upper() if tokens else ""
    arg = tokens[1].strip() if len(tokens) > 1 else ""

    reply_text = ""
    target_claim: Claim | None = None
    target_user: User | None = None

    # 3. Lookup sender user by phone number
    if sender_phone:
        alt_phone = sender_phone.lstrip("+")
        u_stmt = (
            select(User)
            .options(selectinload(User.recipient))
            .where(
                or_(
                    User.phone_e164 == sender_phone,
                    User.phone_e164 == alt_phone,
                    User.phone_e164 == f"+{alt_phone}",
                )
            )
            .order_by(User.created_at.desc())
        )
        res = await db.execute(u_stmt)
        target_user = res.scalars().first()

    if not target_user:
        reply_text = (
            "Your phone number is not linked to a BountyLoop account. "
            "Please register or update your phone in the BountyLoop app."
        )
    else:
        inbound_log.user_id = target_user.id
        recipient = target_user.recipient

        # 4. Command Dispatch
        if command in ("RESCUE", "ACCEPT"):
            if not recipient:
                reply_text = (
                    "Your account is not registered as a recipient organization. "
                    "Only verified food rescue recipients can claim offers."
                )
            else:
                # Find matching claim
                claim_stmt = (
                    select(Claim)
                    .options(
                        selectinload(Claim.donation)
                        .selectinload(Donation.donor)
                        .selectinload(Donor.user)
                    )
                    .where(Claim.recipient_id == recipient.id)
                )

                if arg:
                    # Match full UUID or hex prefix
                    clean_arg = arg.lower().replace("-", "")
                    claim_stmt = claim_stmt.where(
                        or_(
                            cast(Claim.id, String).ilike(f"{clean_arg}%"),
                            func.replace(cast(Claim.id, String), "-", "").ilike(f"{clean_arg}%"),
                        )
                    )
                else:
                    # If no code supplied, pick the single newest offered claim
                    claim_stmt = claim_stmt.where(Claim.status == ClaimStatus.offered).order_by(
                        Claim.offered_at.desc()
                    )

                c_res = await db.execute(claim_stmt)
                claims = c_res.scalars().all()

                if not claims:
                    reply_text = (
                        f"No pending claim offer found matching '{arg}'. "
                        "Reply STATUS to view your active offers."
                    )
                else:
                    target_claim = claims[0]
                    inbound_log.claim_id = target_claim.id
                    claim_code = target_claim.id.hex[:8].upper()

                    if target_claim.status == ClaimStatus.accepted:
                        pickup_addr = (
                            target_claim.donation.pickup_address
                            if target_claim.donation
                            else "Address on file"
                        )
                        reply_text = (
                            f"Claim #{claim_code} is already accepted. "
                            f"Pickup location: {pickup_addr}."
                        )
                    elif target_claim.status != ClaimStatus.offered:
                        reply_text = f"Claim #{claim_code} is {target_claim.status.value} and cannot be accepted."
                    else:
                        # Accept claim
                        now = datetime.now(UTC)
                        target_claim.status = ClaimStatus.accepted
                        target_claim.responded_at = now
                        if target_claim.donation:
                            target_claim.donation.status = DonationStatus.matched

                        await db.commit()
                        await db.refresh(target_claim)

                        donation = target_claim.donation
                        item_name = donation.item.value if donation else "food"
                        weight_str = f"{donation.weight_kg:.1f}kg" if donation else ""
                        pickup_addr = donation.pickup_address if donation else "See app for details"

                        # Notify donor via communication bus
                        if donation and donation.donor and donation.donor.user:
                            await communication_bus.dispatch_claim_accepted(
                                db=db,
                                donor_user_id=donation.donor.user.id,
                                recipient=recipient,
                                donation=donation,
                                claim=target_claim,
                            )

                        # Broadcast WebSocket event
                        await ws_manager.broadcast(
                            "offer_accepted",
                            {
                                "claim_id": str(target_claim.id),
                                "recipient_id": str(recipient.id),
                                "donation_id": str(donation.id) if donation else None,
                                "source": "sms_webhook",
                            },
                        )

                        reply_text = (
                            f"Success! You confirmed rescue #{claim_code} ({weight_str} {item_name}). "
                            f"Pickup address: {pickup_addr}. Thank you for rescuing good food! 💚"
                        )

        elif command == "DECLINE":
            if not recipient:
                reply_text = "Only recipient organizations can decline offers."
            else:
                claim_stmt = select(Claim).where(
                    Claim.recipient_id == recipient.id,
                    Claim.status == ClaimStatus.offered,
                )
                if arg:
                    clean_arg = arg.lower().replace("-", "")
                    claim_stmt = claim_stmt.where(
                        func.replace(cast(Claim.id, String), "-", "").ilike(f"{clean_arg}%")
                    )
                c_res = await db.execute(claim_stmt)
                declined_claim = c_res.scalars().first()

                if declined_claim:
                    declined_claim.status = ClaimStatus.declined
                    declined_claim.responded_at = datetime.now(UTC)
                    await db.commit()
                    claim_code = declined_claim.id.hex[:8].upper()
                    reply_text = f"Claim #{claim_code} declined. Thank you for letting us know."
                else:
                    reply_text = "No pending offer found to decline."

        elif command == "STATUS":
            if not recipient:
                reply_text = "No recipient profile found for your account."
            else:
                stmt = (
                    select(Claim)
                    .options(selectinload(Claim.donation))
                    .where(
                        Claim.recipient_id == recipient.id,
                        Claim.status.in_([ClaimStatus.offered, ClaimStatus.accepted]),
                    )
                    .order_by(Claim.offered_at.desc())
                    .limit(3)
                )
                active_claims = (await db.execute(stmt)).scalars().all()
                if not active_claims:
                    reply_text = "No active claims or offers right now. We'll text you when fresh surplus is nearby!"
                else:
                    lines = ["BountyLoop Active Status:"]
                    for c in active_claims:
                        code = c.id.hex[:8].upper()
                        item = c.donation.item.value if c.donation else "food"
                        lines.append(f"- #{code} [{c.status.value.upper()}]: {item}")
                    reply_text = "\n".join(lines)

        elif command in ("HELP", "INFO", "COMMANDS"):
            reply_text = (
                "BountyLoop SMS Commands:\n"
                "- RESCUE <code>: Accept offer\n"
                "- DECLINE <code>: Decline offer\n"
                "- STATUS: View active claims\n"
                "- HELP: View this menu"
            )

        else:
            reply_text = (
                "Unrecognized command. Reply RESCUE <code> to accept a food rescue offer, "
                "or reply HELP for instructions."
            )

    await db.commit()

    # 5. Content-Type Response Negotiation
    # If client specifically requested JSON, return InboundWebhookResponse
    if accept and "application/json" in accept.lower():
        return InboundWebhookResponse(
            status="ok",
            command=command,
            reply=reply_text,
            claim_id=str(target_claim.id) if target_claim else None,
            user_id=str(target_user.id) if target_user else None,
        )

    # Default: Twilio standard TwiML XML
    twiml_xml = _format_twiml(reply_text)
    return Response(content=twiml_xml, media_type="application/xml")
