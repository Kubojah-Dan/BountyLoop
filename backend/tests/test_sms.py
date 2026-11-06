"""BountyLoop — Twilio SMS Fallback & Communication Bus Test Suite (§Master Plan §6 Phase 9).

Covers:
1. Twilio SMS client: mock dispatch, database audit logging, and hard SMS_DAILY_CAP (20) enforcement.
2. Communication router: push-first routing policy (suppresses SMS when push devices exist, falls back to SMS otherwise).
3. Daily cap exhaustion handling (refusal logged, push/WebSocket remain functional).
4. Inbound Twilio SMS webhook: one-tap 'RESCUE <claim_id>' acceptance lifecycle, donor alert dispatch,
   claim and donation status transitions, phone ownership validation, decline/status/help commands,
   and TwiML XML formatting.
5. Quota usage and manual SMS API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from geoalchemy2.elements import WKTElement
from httpx import AsyncClient, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Claim,
    ClaimStatus,
    Donation,
    DonationStatus,
    Donor,
    DonorKind,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    Recipient,
    RecipientOrgType,
    SmsMessage,
    User,
    UserRole,
)
from app.services.communication import (
    COMMUNICATION_DISPATCH_LOG,
    communication_bus,
)
from app.services.notification import DISPATCHED_NOTIFICATIONS, notification_service
from app.services.sms import (
    DISPATCHED_SMS,
    TwilioSmsClient,
    twilio_sms_client,
)


@pytest.fixture(autouse=True)
async def clean_sms_state(db_session: AsyncSession):
    """Clear in-memory dispatch logs, counters, and sms_messages rows between test runs."""
    DISPATCHED_SMS.clear()
    DISPATCHED_NOTIFICATIONS.clear()
    COMMUNICATION_DISPATCH_LOG.clear()
    twilio_sms_client.reset_daily_count_for_test()
    await db_session.execute(delete(SmsMessage))
    await db_session.commit()
    yield
    DISPATCHED_SMS.clear()
    DISPATCHED_NOTIFICATIONS.clear()
    COMMUNICATION_DISPATCH_LOG.clear()
    twilio_sms_client.reset_daily_count_for_test()


async def _create_test_user_and_recipient(
    db: AsyncSession,
    phone: str,
    name: str = "Austin Food Rescuers",
) -> tuple[User, Recipient]:
    """Helper to create a user with a recipient organization and phone number."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_user_{uuid.uuid4().hex[:8]}",
        email=f"recipient_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.recipient,
        display_name=name,
        org_name=name,
        phone_e164=phone,
    )
    db.add(user)
    await db.flush()

    recipient = Recipient(
        id=uuid.uuid4(),
        user_id=user.id,
        org_type=RecipientOrgType.food_bank,
        address="789 Rescue Blvd, Austin, TX",
        location=WKTElement("POINT(-97.7431 30.2672)", srid=4326),
        capacity_kg_per_day=500.0,
        accepted_items=["produce_fruit", "bread_bakery"],
        is_accepting=True,
    )
    db.add(recipient)
    await db.commit()
    await db.refresh(user)
    await db.refresh(recipient)
    return user, recipient


async def _create_test_donor(
    db: AsyncSession,
    phone: str | None = "+15125550100",
) -> tuple[User, Donor]:
    """Helper to create a donor user and establishment."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_donor_{uuid.uuid4().hex[:8]}",
        email=f"donor_{uuid.uuid4().hex[:8]}@test.org",
        role=UserRole.donor,
        display_name="Austin Organic Bakery",
        phone_e164=phone,
    )
    db.add(user)
    await db.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.grocery,
        address="101 Main St, Austin, TX",
        location=WKTElement("POINT(-97.7400 30.2700)", srid=4326),
    )
    db.add(donor)
    await db.commit()
    await db.refresh(user)
    await db.refresh(donor)
    return user, donor


async def _create_test_donation(
    db: AsyncSession,
    donor: Donor,
    item: FoodCategory = FoodCategory.bread_bakery,
    weight_kg: float = 14.5,
) -> Donation:
    """Helper to create an open donation."""
    now = datetime.now(UTC)
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor.id,
        item=item,
        item_confidence=0.95,
        freshness=FreshnessGrade.fresh,
        freshness_confidence=0.92,
        hazard_flag=HazardFlag.none,
        est_weight_kg=weight_kg,
        expires_at=now + timedelta(hours=24),
        status=DonationStatus.open,
        needs_review=False,
    )
    db.add(donation)
    await db.commit()
    await db.refresh(donation)
    return donation


# ─────────────────────────────────────────────────────────────────────────────
# 1. Twilio SMS Client Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sms_client_mock_dispatch_and_audit(db_session: AsyncSession):
    """Verify mock SMS dispatch, message SID generation, in-memory log, and DB audit row."""
    client = TwilioSmsClient(daily_cap=20)
    to_phone = "+15125550199"
    body = "Test BountyLoop alert message"

    result = await client.send_sms(to_phone=to_phone, body=body, db=db_session)

    assert result.success is True
    assert result.status == "mock_sent"
    assert result.message_sid is not None
    assert result.message_sid.startswith("SMmock_")
    assert result.daily_count == 1
    assert result.daily_cap == 20

    # In-memory dispatch check
    assert len(DISPATCHED_SMS) == 1
    assert DISPATCHED_SMS[0]["to"] == to_phone
    assert DISPATCHED_SMS[0]["body"] == body

    # Database audit check
    stmt = select(SmsMessage).where(SmsMessage.to_phone == to_phone)
    msg_row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert msg_row is not None
    assert msg_row.body == body
    assert msg_row.status == "mock_sent"
    assert msg_row.direction == "outbound"


@pytest.mark.asyncio
async def test_sms_client_daily_cap_enforcement(db_session: AsyncSession):
    """Enforce the hard SMS_DAILY_CAP. Outbound attempts exceeding cap must be refused and logged."""
    small_cap = 3
    client = TwilioSmsClient(daily_cap=small_cap)
    to_phone = "+15125550123"

    # Send up to cap
    for i in range(small_cap):
        res = await client.send_sms(to_phone=to_phone, body=f"Message {i + 1}", db=db_session)
        assert res.success is True
        assert res.daily_count == i + 1

    # 4th message must be capped
    capped_res = await client.send_sms(
        to_phone=to_phone, body="Message 4 (Over Cap)", db=db_session
    )
    assert capped_res.success is False
    assert capped_res.status == "capped"
    assert "Daily SMS cap" in (capped_res.error or "")
    assert capped_res.daily_count == small_cap

    # Check usage stats
    usage = await client.get_daily_usage(db_session)
    assert usage.sent_today == small_cap
    assert usage.remaining == 0
    assert usage.is_capped is True

    # Capped attempt must be recorded in DB with status='capped'
    stmt = select(SmsMessage).where(SmsMessage.status == "capped")
    capped_msgs = (await db_session.execute(stmt)).scalars().all()
    assert len(capped_msgs) >= 1
    assert "exceeded" in capped_msgs[0].error_message.lower()


@pytest.mark.asyncio
async def test_sms_client_live_dispatch_twiml_api_mock(db_session: AsyncSession):
    """Simulate live Twilio REST API 201 Created and 400 Bad Request responses."""
    client = TwilioSmsClient(
        account_sid="ACmockaccountsid1234567890abcdef",
        auth_token="authtoken1234567890abcdef",
        from_number="+18005550199",
        daily_cap=20,
    )
    assert client.is_configured is True

    # 1. Simulate Success (201 Created)
    mock_201 = Response(
        status_code=201,
        json={"sid": "SMlive_success_12345", "status": "queued"},
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_201):
        res = await client.send_sms(to_phone="+15125550101", body="Live Twilio Test", db=db_session)
        assert res.success is True
        assert res.status == "sent"
        assert res.message_sid == "SMlive_success_12345"

    # 2. Simulate Failure (400 Bad Request)
    mock_400 = Response(
        status_code=400,
        text="Invalid To phone number",
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_400):
        fail_res = await client.send_sms(
            to_phone="+invalid", body="Live Twilio Fail Test", db=db_session
        )
        assert fail_res.success is False
        assert fail_res.status == "failed"
        assert "Twilio API error 400" in (fail_res.error or "")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Communication Bus (Push-First & SMS Fallback) Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_communication_bus_push_first_suppresses_sms(db_session: AsyncSession):
    """When a recipient has registered FCM device tokens, push is delivered and SMS is suppressed."""
    user, _ = await _create_test_user_and_recipient(
        db_session, phone="+15125550201", name="Austin Hope Shelter"
    )

    # Register FCM token for user
    await notification_service.register_device(
        db=db_session,
        user_id=user.id,
        fcm_token=f"fcm_token_{uuid.uuid4().hex[:16]}",
        platform="android",
    )

    receipt = await communication_bus.dispatch_notification(
        db=db_session,
        user_id=user.id,
        title="Surplus Available!",
        body="Fresh bread ready for pickup",
    )

    # Must be delivered via Push
    assert receipt.primary_channel == "push"
    assert receipt.push_delivered is True
    assert receipt.push_device_count >= 1
    # SMS must NOT have been sent
    assert receipt.sms_dispatched is False
    assert len(DISPATCHED_SMS) == 0


@pytest.mark.asyncio
async def test_communication_bus_fallback_to_sms_when_no_push_devices(db_session: AsyncSession):
    """When a recipient has no registered FCM push devices, the router falls back gracefully to SMS."""
    user, _ = await _create_test_user_and_recipient(
        db_session, phone="+15125550202", name="Eastside Food Pantry"
    )

    receipt = await communication_bus.dispatch_notification(
        db=db_session,
        user_id=user.id,
        title="Urgent Rescue Alert",
        body="Apples and produce need rescue by 6 PM",
    )

    # Must have fallen back to SMS
    assert receipt.primary_channel == "sms"
    assert receipt.push_delivered is False
    assert receipt.sms_dispatched is True
    assert receipt.sms_result is not None
    assert receipt.sms_result.success is True
    assert len(DISPATCHED_SMS) == 1
    assert DISPATCHED_SMS[0]["to"] == "+15125550202"


@pytest.mark.asyncio
async def test_communication_bus_handles_sms_daily_cap_exhaustion(db_session: AsyncSession):
    """When push is unavailable and daily SMS cap is exhausted, delivery logs capped status safely."""
    # Use small cap client for communication bus test
    small_cap_client = TwilioSmsClient(daily_cap=1)
    with patch("app.services.communication.communication_bus.sms_client", small_cap_client):
        user, _ = await _create_test_user_and_recipient(
            db_session, phone="+15125550203", name="Cap Test Center"
        )

        # 1st dispatch consumes the single SMS quota
        r1 = await communication_bus.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="First Alert",
            body="First notice",
        )
        assert r1.sms_dispatched is True

        # 2nd dispatch must hit cap
        r2 = await communication_bus.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Second Alert",
            body="Second notice over cap",
        )
        assert r2.primary_channel == "sms"
        assert r2.sms_dispatched is False
        assert r2.sms_result is not None
        assert r2.sms_result.status == "capped"
        # WebSocket broadcast still succeeded
        assert r2.websocket_broadcast is True


@pytest.mark.asyncio
async def test_communication_bus_domain_helpers(db_session: AsyncSession):
    """Verify dispatch_claim_offer, dispatch_claim_accepted, and dispatch_pickup_reminder formats."""
    d_user, donor = await _create_test_donor(db_session)
    r_user, recipient = await _create_test_user_and_recipient(db_session, phone="+15125550204")
    donation = await _create_test_donation(db_session, donor, weight_kg=12.0)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.offered,
        score=88.5,
        score_breakdown={"distance_km": 1.5},
        offered_at=datetime.now(UTC),
    )
    db_session.add(claim)
    await db_session.commit()
    await db_session.refresh(claim)

    # 1. dispatch_claim_offer
    receipt = await communication_bus.dispatch_claim_offer(
        db=db_session,
        recipient=recipient,
        donation=donation,
        claim=claim,
    )
    assert receipt.sms_dispatched is True
    assert len(DISPATCHED_SMS) == 1
    sent_text = DISPATCHED_SMS[0]["body"]
    assert "RESCUE" in sent_text
    assert claim.id.hex[:8].upper() in sent_text

    # 2. dispatch_claim_accepted
    r_acc = await communication_bus.dispatch_claim_accepted(
        db=db_session,
        donor_user_id=d_user.id,
        recipient=recipient,
        donation=donation,
        claim=claim,
    )
    assert r_acc.sms_dispatched is True
    assert "accepted your donation" in DISPATCHED_SMS[1]["body"]

    # 3. dispatch_pickup_reminder
    r_rem = await communication_bus.dispatch_pickup_reminder(
        db=db_session,
        recipient=recipient,
        donation=donation,
        claim=claim,
    )
    assert r_rem.sms_dispatched is True
    assert "Pickup for" in DISPATCHED_SMS[2]["body"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Inbound Twilio Webhook Tests (POST /v1/sms/webhook)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inbound_webhook_rescue_confirm_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify one-tap RESCUE <claim_id> flow via inbound Twilio webhook:

    - Recipient texts 'RESCUE <claim_code>'
    - Claim transitions to accepted, donation to matched
    - Donor notification dispatched
    - TwiML XML response contains pickup address
    """
    phone = "+15125550301"
    _, donor = await _create_test_donor(db_session, phone="+15125550302")
    _, recipient = await _create_test_user_and_recipient(
        db_session, phone=phone, name="South Austin Food Hub"
    )
    donation = await _create_test_donation(db_session, donor, weight_kg=25.0)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.offered,
        score=92.0,
        offered_at=datetime.now(UTC),
    )
    db_session.add(claim)
    await db_session.commit()
    await db_session.refresh(claim)

    claim_code = claim.id.hex[:8].upper()

    # Post inbound Twilio webhook as standard form-urlencoded data
    resp = await client.post(
        "/v1/sms/webhook",
        data={
            "From": phone,
            "To": "+18005550100",
            "Body": f"RESCUE {claim_code}",
            "MessageSid": f"SM_test_{uuid.uuid4().hex[:16]}",
        },
    )

    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    xml_content = resp.text
    assert "<Response>" in xml_content
    assert "<Message>" in xml_content
    assert f"rescue #{claim_code.lower()}" in xml_content.lower()
    assert "101 Main St" in xml_content  # Pickup address

    # Verify Database state
    c_stmt = select(Claim).where(Claim.id == claim.id)
    updated_claim = (await db_session.execute(c_stmt)).scalar_one()
    assert updated_claim.status == ClaimStatus.accepted
    assert updated_claim.responded_at is not None

    d_stmt = select(Donation).where(Donation.id == donation.id)
    updated_donation = (await db_session.execute(d_stmt)).scalar_one()
    assert updated_donation.status == DonationStatus.matched

    # Verify donor notification was dispatched
    assert any(
        "accepted your donation" in s["body"] or "Donation Matched" in s.get("title", "")
        for s in (DISPATCHED_SMS + DISPATCHED_NOTIFICATIONS)
    )


@pytest.mark.asyncio
async def test_inbound_webhook_accept_alias_and_json_negotiation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify 'ACCEPT <claim_code>' alias, case-insensitivity, and JSON response negotiation."""
    phone = "+15125550303"
    _, donor = await _create_test_donor(db_session)
    _, recipient = await _create_test_user_and_recipient(
        db_session, phone=phone, name="Cedar Park Pantry"
    )
    donation = await _create_test_donation(db_session, donor)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.offered,
        score=85.0,
        offered_at=datetime.now(UTC),
    )
    db_session.add(claim)
    await db_session.commit()

    claim_code = claim.id.hex[:8].lower()

    # Request with Accept: application/json header
    resp = await client.post(
        "/v1/sms/webhook",
        headers={"Accept": "application/json"},
        json={
            "From": phone,
            "To": "+18005550100",
            "Body": f"accept {claim_code}",
            "MessageSid": f"SM_test_{uuid.uuid4().hex[:16]}",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["command"] == "ACCEPT"
    assert data["claim_id"] == str(claim.id)
    assert "Success!" in data["reply"]


@pytest.mark.asyncio
async def test_inbound_webhook_unregistered_phone(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Unregistered phone number receives an informative rejection TwiML message."""
    resp = await client.post(
        "/v1/sms/webhook",
        data={
            "From": "+19995550999",
            "To": "+18005550100",
            "Body": "RESCUE ABCD1234",
        },
    )

    assert resp.status_code == 200
    assert "not linked to a BountyLoop account" in resp.text


@pytest.mark.asyncio
async def test_inbound_webhook_unauthorized_claim_cross_access(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Recipient A cannot accept a claim offered to Recipient B."""
    _, donor = await _create_test_donor(db_session)
    _, recipient_a = await _create_test_user_and_recipient(
        db_session, phone="+15125550401", name="Pantry A"
    )
    _, recipient_b = await _create_test_user_and_recipient(
        db_session, phone="+15125550402", name="Pantry B"
    )
    donation = await _create_test_donation(db_session, donor)

    # Claim offered to Recipient B
    claim_b = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient_b.id,
        status=ClaimStatus.offered,
        score=87.0,
        offered_at=datetime.now(UTC),
    )
    db_session.add(claim_b)
    await db_session.commit()

    code_b = claim_b.id.hex[:8].upper()

    # Recipient A attempts to rescue Recipient B's claim
    resp = await client.post(
        "/v1/sms/webhook",
        data={
            "From": "+15125550401",  # Pantry A's phone
            "To": "+18005550100",
            "Body": f"RESCUE {code_b}",
        },
    )

    assert resp.status_code == 200
    assert "No pending claim offer found matching" in resp.text

    # Claim must remain in offered state
    c_stmt = select(Claim).where(Claim.id == claim_b.id)
    c_fresh = (await db_session.execute(c_stmt)).scalar_one()
    assert c_fresh.status == ClaimStatus.offered


@pytest.mark.asyncio
async def test_inbound_webhook_decline_and_status_and_help(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify DECLINE, STATUS, HELP, and unrecognized command handlers."""
    phone = "+15125550501"
    _, donor = await _create_test_donor(db_session)
    _, recipient = await _create_test_user_and_recipient(
        db_session, phone=phone, name="Round Rock Center"
    )
    donation = await _create_test_donation(db_session, donor)

    claim = Claim(
        id=uuid.uuid4(),
        donation_id=donation.id,
        recipient_id=recipient.id,
        status=ClaimStatus.offered,
        score=84.0,
        offered_at=datetime.now(UTC),
    )
    db_session.add(claim)
    await db_session.commit()
    code = claim.id.hex[:8].upper()

    # 1. STATUS command
    s_resp = await client.post(
        "/v1/sms/webhook",
        data={"From": phone, "Body": "STATUS"},
    )
    assert s_resp.status_code == 200
    assert "BountyLoop Active Status" in s_resp.text
    assert f"#{code} [OFFERED]" in s_resp.text

    # 2. DECLINE command
    d_resp = await client.post(
        "/v1/sms/webhook",
        data={"From": phone, "Body": f"DECLINE {code}"},
    )
    assert d_resp.status_code == 200
    assert f"Claim #{code} declined" in d_resp.text

    c_stmt = select(Claim).where(Claim.id == claim.id)
    updated_c = (await db_session.execute(c_stmt)).scalar_one()
    assert updated_c.status == ClaimStatus.declined

    # 3. HELP command
    h_resp = await client.post(
        "/v1/sms/webhook",
        data={"From": phone, "Body": "HELP"},
    )
    assert h_resp.status_code == 200
    assert "BountyLoop SMS Commands" in h_resp.text
    assert "RESCUE" in h_resp.text

    # 4. Unrecognized command
    u_resp = await client.post(
        "/v1/sms/webhook",
        data={"From": phone, "Body": "HELLO WHAT IS THIS"},
    )
    assert u_resp.status_code == 200
    assert "Unrecognized command" in u_resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 4. Quota and Manual Dispatch API Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sms_api_usage_and_manual_send(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify GET /v1/sms/usage and POST /v1/sms/send endpoints."""
    # 1. Check initial usage
    u1 = await client.get("/v1/sms/usage")
    assert u1.status_code == 200
    u1_data = u1.json()
    assert "sent_today" in u1_data
    assert u1_data["daily_cap"] == 20
    initial_sent = u1_data["sent_today"]

    # 2. Send manual SMS
    send_resp = await client.post(
        "/v1/sms/send",
        json={
            "to_phone": "+15125550601",
            "body": "Manual alert test message via API",
        },
    )
    assert send_resp.status_code == 200
    send_data = send_resp.json()
    assert send_data["success"] is True
    assert send_data["status"] == "mock_sent"
    assert send_data["daily_count"] == initial_sent + 1

    # 3. Verify usage updated
    u2 = await client.get("/v1/sms/usage")
    assert u2.status_code == 200
    u2_data = u2.json()
    assert u2_data["sent_today"] == initial_sent + 1
    assert u2_data["remaining"] == 20 - (initial_sent + 1)
