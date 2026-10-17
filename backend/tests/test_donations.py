"""BountyLoop — Integration Tests for Donation API (Photo-to-Donate flow)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.db.models.enums import FoodCategory, FreshnessGrade, HazardFlag


def create_test_image_bytes(color=(100, 200, 100)) -> bytes:
    """Generate in-memory test JPEG bytes."""
    img = Image.new("RGB", (120, 120), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


MOCK_DONOR_CLAIMS = {
    "uid": "fb_donor_test_user_01",
    "email": "donor_tester@bountyloop.org",
    "name": "Jane Donor",
}

MOCK_RECIPIENT_CLAIMS = {
    "uid": "fb_recipient_test_user_01",
    "email": "recipient_tester@bountyloop.org",
    "name": "Bob Recipient",
}


@pytest.mark.asyncio
async def test_create_and_confirm_donation_happy_path(client: AsyncClient) -> None:
    """Donor uploads photo -> draft created -> donor confirms -> status=open."""
    img_bytes = create_test_image_bytes(color=(220, 50, 50))

    mock_cv_res = {
        "item": FoodCategory.produce_fruit,
        "item_confidence": 0.95,
        "freshness": FreshnessGrade.grade_3_fresh,
        "freshness_confidence": 0.94,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {"item": "item_v1", "freshness": "freshness_v2"},
        "latency_ms": 120.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch("app.services.cv_client.CVClient.predict", new_callable=AsyncMock) as mock_predict,
    ):
        mock_predict.return_value = mock_cv_res

        # 1. POST /v1/donations
        resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            data={"est_weight_kg": "3.5", "address": "100 Congress Ave, Austin, TX"},
            files=[("files", ("apples.jpg", img_bytes, "image/jpeg"))],
        )

        assert resp.status_code == 201
        data = resp.json()
        donation_id = data["id"]
        assert data["status"] == "draft"
        assert data["item"] == "produce_fruit"
        assert data["freshness"] == "grade_3_fresh"
        assert data["est_weight_kg"] == 3.5
        assert data["needs_review"] is False
        assert len(data["photo_paths"]) == 1

        # 2. PATCH /v1/donations/{id}/confirm
        confirm_resp = await client.patch(
            f"/v1/donations/{donation_id}/confirm",
            headers={"Authorization": "Bearer fake_donor_token"},
            json={
                "item": "produce_fruit",
                "freshness": "grade_2_good",
                "est_weight_kg": 4.0,
            },
        )
        assert confirm_resp.status_code == 200
        confirmed_data = confirm_resp.json()
        assert confirmed_data["status"] == "open"
        assert confirmed_data["freshness"] == "grade_2_good"
        assert confirmed_data["est_weight_kg"] == 4.0

        # 3. GET /v1/donations/{id}
        get_resp = await client.get(
            f"/v1/donations/{donation_id}",
            headers={"Authorization": "Bearer fake_donor_token"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "open"

        # 4. GET /v1/donations/{id}/photos/0
        photo_resp = await client.get(
            f"/v1/donations/{donation_id}/photos/0",
            headers={"Authorization": "Bearer fake_donor_token"},
        )
        assert photo_resp.status_code == 200
        assert photo_resp.headers["content-type"] == "image/jpeg"
        assert len(photo_resp.content) > 0


@pytest.mark.asyncio
async def test_cv_outage_fallback_creates_needs_review(client: AsyncClient) -> None:
    """When CV service is down, donation succeeds with needs_review=True and ReviewQueue item."""
    img_bytes = create_test_image_bytes(color=(10, 80, 180))

    fallback_res = {
        "item": FoodCategory.other_unclassified,
        "item_confidence": 0.0,
        "freshness": FreshnessGrade.grade_1_poor,
        "freshness_confidence": 0.0,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.0,
        "action": "human_review_queue",
        "needs_review": True,
        "review_reason": "low_confidence",
        "model_versions": {"cv_status": "offline_fallback"},
        "latency_ms": 0.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch("app.services.cv_client.CVClient.predict", new_callable=AsyncMock) as mock_predict,
    ):
        mock_predict.return_value = fallback_res

        resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            data={"est_weight_kg": "2.0"},
            files=[("files", ("canned_soup.jpg", img_bytes, "image/jpeg"))],
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["needs_review"] is True
        assert data["item"] == "other_unclassified"
        assert data["model_versions"]["cv_status"] == "offline_fallback"


@pytest.mark.asyncio
async def test_hazard_flag_triggers_review_queue(client: AsyncClient) -> None:
    """Formalin/contamination hazard detection flags donation for human review."""
    img_bytes = create_test_image_bytes(color=(250, 200, 10))

    hazard_res = {
        "item": FoodCategory.produce_fruit,
        "item_confidence": 0.98,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.95,
        "hazard_flag": HazardFlag.suspected_contamination_or_formalin,
        "hazard_confidence": 0.88,
        "action": "human_review_queue",
        "needs_review": True,
        "review_reason": "hazard",
        "model_versions": {"hazard": "hazard_v1"},
        "latency_ms": 110.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch("app.services.cv_client.CVClient.predict", new_callable=AsyncMock) as mock_predict,
    ):
        mock_predict.return_value = hazard_res

        resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[("files", ("mango.jpg", img_bytes, "image/jpeg"))],
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["needs_review"] is True
        assert data["hazard_flag"] == "suspected_contamination_or_formalin"


@pytest.mark.asyncio
async def test_duplicate_photo_rejection(client: AsyncClient) -> None:
    """Uploading the exact same image consecutively triggers 409 Conflict."""
    img_bytes = create_test_image_bytes(color=(88, 12, 199))

    mock_cv = {
        "item": FoodCategory.bread_bakery,
        "item_confidence": 0.92,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.90,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {},
        "latency_ms": 50.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch(
            "app.services.cv_client.CVClient.predict", new_callable=AsyncMock, return_value=mock_cv
        ),
    ):
        # First submission succeeds
        resp1 = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[("files", ("bread.jpg", img_bytes, "image/jpeg"))],
        )
        assert resp1.status_code == 201

        # Second submission with identical photo bytes triggers 409
        resp2 = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[("files", ("bread.jpg", img_bytes, "image/jpeg"))],
        )
        assert resp2.status_code == 409
        assert "Duplicate" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_donation(client: AsyncClient) -> None:
    """Donor can cancel draft/open donation; cancelled donation cannot be confirmed."""
    img_bytes = create_test_image_bytes(color=(40, 40, 40))

    mock_cv = {
        "item": FoodCategory.produce_vegetable,
        "item_confidence": 0.91,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.90,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {},
        "latency_ms": 60.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch(
            "app.services.cv_client.CVClient.predict", new_callable=AsyncMock, return_value=mock_cv
        ),
    ):
        resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[("files", ("spinach.jpg", img_bytes, "image/jpeg"))],
        )
        donation_id = resp.json()["id"]

        # Cancel donation
        del_resp = await client.delete(
            f"/v1/donations/{donation_id}",
            headers={"Authorization": "Bearer fake_donor_token"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "cancelled"

        # Attempt to confirm cancelled donation fails with 409
        confirm_resp = await client.patch(
            f"/v1/donations/{donation_id}/confirm",
            headers={"Authorization": "Bearer fake_donor_token"},
            json={"item": "produce_vegetable"},
        )
        assert confirm_resp.status_code == 409


@pytest.mark.asyncio
async def test_upload_limits_and_validation(client: AsyncClient) -> None:
    """Validate empty file and >3 files constraints."""
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS):
        # Empty file -> 400
        empty_resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[("files", ("empty.jpg", b"", "image/jpeg"))],
        )
        assert empty_resp.status_code == 400

        # More than 3 photos -> 400
        img = create_test_image_bytes()
        too_many_resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            files=[
                ("files", ("1.jpg", img, "image/jpeg")),
                ("files", ("2.jpg", img, "image/jpeg")),
                ("files", ("3.jpg", img, "image/jpeg")),
                ("files", ("4.jpg", img, "image/jpeg")),
            ],
        )
        assert too_many_resp.status_code == 400
        assert "Maximum" in too_many_resp.json()["detail"]
