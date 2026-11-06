"""BountyLoop — Integration Tests for Claims, Offers, and Devices API (§6 Phase 6)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.db.models.enums import FoodCategory, FreshnessGrade, HazardFlag
from app.services.notification import DISPATCHED_NOTIFICATIONS


def create_test_image_bytes(color=(120, 180, 120)) -> bytes:
    """Generate in-memory test JPEG bytes."""
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


MOCK_DONOR_CLAIMS = {
    "uid": "fb_donor_claim_test_01",
    "email": "donor_claim@bountyloop.org",
    "name": "Sarah Donor",
}

MOCK_RECIPIENT_CLAIMS = {
    "uid": "fb_recipient_claim_test_01",
    "email": "recipient_claim@bountyloop.org",
    "name": "Austin Community Food Hub",
}


@pytest.mark.asyncio
async def test_register_device_token(client: AsyncClient) -> None:
    """Register FCM device token for push notifications."""
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS):
        resp = await client.post(
            "/v1/devices",
            headers={"Authorization": "Bearer fake_token"},
            json={"fcm_token": "fcm_test_device_token_xyz_987", "platform": "android"},
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_claim_lifecycle_pickup_and_impact(client: AsyncClient) -> None:
    """End-to-end: Donor creates open donation -> Recipient claims -> Picked up -> Impact computed."""
    img_bytes = create_test_image_bytes(color=(210, 80, 50))
    DISPATCHED_NOTIFICATIONS.clear()

    mock_cv = {
        "item": FoodCategory.produce_fruit,
        "item_confidence": 0.94,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.91,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {"item": "item_v1", "freshness": "freshness_v2"},
        "latency_ms": 110.0,
    }

    # 1. Donor registers device and creates & confirms donation
    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch(
            "app.services.cv_client.CVClient.predict", new_callable=AsyncMock, return_value=mock_cv
        ),
    ):
        donor_headers = {"Authorization": "Bearer fake_donor_token"}
        await client.post(
            "/v1/devices",
            headers=donor_headers,
            json={"fcm_token": "fcm_donor_token_123", "platform": "ios"},
        )

        create_resp = await client.post(
            "/v1/donations",
            headers=donor_headers,
            data={"est_weight_kg": "12.0", "address": "200 E 6th St, Austin, TX"},
            files=[("files", ("peaches.jpg", img_bytes, "image/jpeg"))],
        )
        assert create_resp.status_code == 201
        donation_id = create_resp.json()["id"]

        confirm_resp = await client.patch(
            f"/v1/donations/{donation_id}/confirm",
            headers=donor_headers,
            json={"item": "produce_fruit", "freshness": "grade_2_good", "est_weight_kg": 12.0},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "open"

    # 2. Recipient browses offers
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_RECIPIENT_CLAIMS):
        recip_headers = {"Authorization": "Bearer fake_recip_token"}

        # Register role as recipient
        await client.post(
            "/v1/me/role",
            headers=recip_headers,
            json={"role": "recipient", "org_name": "Austin Community Food Hub"},
        )

        offers_resp = await client.get(
            "/v1/offers?radius_km=30.0",
            headers=recip_headers,
        )
        assert offers_resp.status_code == 200
        offers = offers_resp.json()
        target_offer = next((o for o in offers if o["id"] == donation_id), None)
        assert target_offer is not None
        assert target_offer["item"] == "produce_fruit"
        assert target_offer["est_weight_kg"] == 12.0
        assert target_offer["hours_remaining"] > 0

        # 3. Recipient claims the donation
        claim_resp = await client.post(
            "/v1/claims",
            headers=recip_headers,
            json={"donation_id": donation_id},
        )
        assert claim_resp.status_code == 201
        claim_data = claim_resp.json()
        assert claim_data["status"] == "accepted"
        assert claim_data["donation"]["status"] == "matched"
        claim_id = claim_data["id"]

        # Verify donor push notification was dispatched
        matched_notifications = [
            n for n in DISPATCHED_NOTIFICATIONS if n["data"].get("type") == "donation_matched"
        ]
        assert len(matched_notifications) >= 1
        assert matched_notifications[-1]["data"]["donation_id"] == str(donation_id)

        # 4. View active claims
        my_claims_resp = await client.get("/v1/claims", headers=recip_headers)
        assert my_claims_resp.status_code == 200
        assert any(c["id"] == claim_id for c in my_claims_resp.json())

        # 5. Confirm pickup with proof photo
        pickup_resp = await client.post(
            f"/v1/claims/{claim_id}/pickup",
            headers=recip_headers,
            json={"proof_photo_path": "photos/proofs/pickup_1.jpg", "notes": "Picked up on time."},
        )
        assert pickup_resp.status_code == 200
        pickup_data = pickup_resp.json()
        assert pickup_data["status"] == "picked_up"
        assert pickup_data["donation"]["status"] == "completed"

        # 6. Verify impact metrics
        assert pickup_data["impact"] is not None
        assert pickup_data["impact"]["kg_rescued"] == 12.0
        # 12 kg / 1.2 kg per meal = 10 meals
        assert pickup_data["impact"]["meals_equivalent"] == 10.0
        # 12 kg * 2.5 kg CO2e / kg = 30.0 kg CO2e
        assert pickup_data["impact"]["co2e_avoided_kg"] == 30.0


@pytest.mark.asyncio
async def test_decline_claim_reverts_donation_to_open(client: AsyncClient) -> None:
    """Declining a claim resets the donation status back to open."""
    img_bytes = create_test_image_bytes(color=(140, 90, 200))

    mock_cv = {
        "item": FoodCategory.bread_bakery,
        "item_confidence": 0.90,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.88,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {},
        "latency_ms": 90.0,
    }

    # 1. Create open donation
    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch(
            "app.services.cv_client.CVClient.predict", new_callable=AsyncMock, return_value=mock_cv
        ),
    ):
        donor_headers = {"Authorization": "Bearer fake_donor_token"}
        create_resp = await client.post(
            "/v1/donations",
            headers=donor_headers,
            data={"est_weight_kg": "5.0"},
            files=[("files", ("bread.jpg", img_bytes, "image/jpeg"))],
        )
        don_id = create_resp.json()["id"]
        await client.patch(
            f"/v1/donations/{don_id}/confirm",
            headers=donor_headers,
            json={"item": "bread_bakery", "freshness": "grade_2_good"},
        )

    # 2. Claim donation as recipient
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_RECIPIENT_CLAIMS):
        recip_headers = {"Authorization": "Bearer fake_recip_token"}
        claim_resp = await client.post(
            "/v1/claims",
            headers=recip_headers,
            json={"donation_id": don_id},
        )
        assert claim_resp.status_code == 201
        claim_id = claim_resp.json()["id"]

        # 3. Decline claim
        decline_resp = await client.post(
            f"/v1/claims/{claim_id}/decline",
            headers=recip_headers,
            json={"reason": "Transport van broke down."},
        )
        assert decline_resp.status_code == 200

        # 4. Check donation is open again
        offers_resp = await client.get("/v1/offers", headers=recip_headers)
        assert offers_resp.status_code == 200
        assert any(o["id"] == don_id for o in offers_resp.json())
