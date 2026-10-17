"""BountyLoop — Integration Tests for Review Queue API (Human-in-the-Loop Triage)."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.db.models.enums import FoodCategory, FreshnessGrade, HazardFlag


def create_test_image_bytes(color=(80, 160, 240)) -> bytes:
    """Generate in-memory test JPEG bytes."""
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


MOCK_DONOR_CLAIMS = {
    "uid": "fb_donor_review_test_01",
    "email": "donor_review@bountyloop.org",
    "name": "Donor User",
}

MOCK_VOLUNTEER_CLAIMS = {
    "uid": "fb_volunteer_review_test_01",
    "email": "volunteer_review@bountyloop.org",
    "name": "Sam Volunteer",
}

MOCK_ADMIN_CLAIMS = {
    "uid": "fb_admin_review_test_01",
    "email": "admin_review@bountyloop.org",
    "name": "Alice Admin",
}


@pytest.mark.asyncio
async def test_review_queue_rbac(client: AsyncClient) -> None:
    """Ensure non-operators (donors/recipients) cannot access review queue."""
    # 1. Unauthenticated -> 401
    resp_anon = await client.get("/v1/review-queue")
    assert resp_anon.status_code == 401

    # 2. Donor registered and authenticated -> 403 Forbidden
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS):
        resp_donor = await client.get(
            "/v1/review-queue",
            headers={"Authorization": "Bearer fake_donor_token"},
        )
        assert resp_donor.status_code == 403


@pytest.mark.asyncio
async def test_review_queue_listing_and_resolution(client: AsyncClient) -> None:
    """Test full cycle: low-confidence donation -> review queue -> volunteer adjudication."""
    img_bytes = create_test_image_bytes()

    # Low-confidence prediction triggers review
    low_conf_cv = {
        "item": FoodCategory.other_unclassified,
        "item_confidence": 0.40,
        "freshness": FreshnessGrade.grade_1_poor,
        "freshness_confidence": 0.45,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.90,
        "action": "human_review",
        "needs_review": True,
        "review_reason": "Low item confidence (0.40 < 0.65)",
        "model_versions": {"item": "item_v1", "freshness": "freshness_v2"},
        "latency_ms": 110.0,
    }

    # 1. Create donation as donor
    with (
        patch("app.core.security.verify_firebase_token", return_value=MOCK_DONOR_CLAIMS),
        patch("app.services.cv_client.CVClient.predict", new_callable=AsyncMock) as mock_predict,
    ):
        mock_predict.return_value = low_conf_cv

        create_resp = await client.post(
            "/v1/donations",
            headers={"Authorization": "Bearer fake_donor_token"},
            data={"est_weight_kg": "2.0"},
            files=[("files", ("mystery.jpg", img_bytes, "image/jpeg"))],
        )
        assert create_resp.status_code == 201
        don_data = create_resp.json()
        assert don_data["needs_review"] is True
        donation_id = don_data["id"]

    # 2. Provision volunteer and set role
    with patch("app.core.security.verify_firebase_token", return_value=MOCK_VOLUNTEER_CLAIMS):
        headers_vol = {"Authorization": "Bearer fake_vol_token"}
        role_resp = await client.post(
            "/v1/me/role",
            headers=headers_vol,
            json={"role": "volunteer", "org_name": "Austin Community Food Rescue"},
        )
        assert role_resp.status_code == 200

        # Query pending review queue
        queue_resp = await client.get(
            "/v1/review-queue?status=pending&limit=100",
            headers=headers_vol,
        )
        assert queue_resp.status_code == 200
        queue_data = queue_resp.json()
        assert queue_data["total"] >= 1
        items = queue_data["items"]
        target_item = next((it for it in items if it["donation_id"] == donation_id), None)
        assert target_item is not None
        assert target_item["status"] == "pending"
        assert target_item["donation"]["id"] == donation_id
        review_id = target_item["id"]

        # 3. Resolve review item with operator overrides
        resolve_resp = await client.post(
            f"/v1/review-queue/{review_id}/resolve",
            headers=headers_vol,
            json={
                "status": "resolved",
                "override_item": "bread_bakery",
                "override_freshness": "grade_2_good",
                "override_weight_kg": 2.5,
                "approve_for_dispatch": True,
                "note": "Operator verified fresh artisan bread.",
            },
        )
        assert resolve_resp.status_code == 200
        resolved_data = resolve_resp.json()
        assert resolved_data["status"] == "resolved"
        assert resolved_data["donation"]["item"] == "bread_bakery"
        assert resolved_data["donation"]["freshness"] == "grade_2_good"
        assert resolved_data["donation"]["est_weight_kg"] == 2.5
        assert resolved_data["donation"]["needs_review"] is False
        assert resolved_data["donation"]["status"] == "open"
        assert resolved_data["note"] == "Operator verified fresh artisan bread."

        # 4. Check that pending queue no longer returns this item
        queue_after = await client.get(
            "/v1/review-queue?status=pending",
            headers=headers_vol,
        )
        assert queue_after.status_code == 200
        pending_after = queue_after.json()["items"]
        assert not any(it["id"] == review_id for it in pending_after)

        # 5. Check 404 on non-existent review ID
        random_id = str(uuid.uuid4())
        resp_404 = await client.post(
            f"/v1/review-queue/{random_id}/resolve",
            headers=headers_vol,
            json={"status": "resolved"},
        )
        assert resp_404.status_code == 404
