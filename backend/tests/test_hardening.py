"""BountyLoop — Hardening, Privacy, Security & Observability Test Suite (Phase 12).

Tests:
1. Security: Magic bytes validation rejects renamed text/binary files with 400.
2. Security: Oversized upload exceeding MAX_UPLOAD_MB is rejected with 413.
3. Security: Internal service token dependency enforces authorization.
4. Privacy: EXIF and GPS metadata is stripped server-side before persistence.
5. Privacy: Retraining consent toggle is stored on user profile.
6. Privacy: DELETE /v1/me/data wipes photos from disk and anonymizes PII.
7. Offline Mobile: Idempotency-Key prevents duplicate donation creation on retry/sync.
8. Observability: GET /metrics exposes valid Prometheus exposition text.
9. Observability: GET /healthz?deep=true executes deep DB and CV probes.
10. Resilience: CV Circuit Breaker trips after 3 failures and degrades to review queue.
11. Secret Scan: Asserts no hardcoded private keys or live credentials exist in source.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import (
    Donation,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    User,
)
from app.services.cv_client import cv_client
from app.services.security import (
    cv_circuit_breaker,
    validate_image_upload,
    verify_internal_service_token,
)
from app.services.storage import save_donation_photo

settings = get_settings()

MOCK_DONOR_AUTH = {
    "uid": "fb_donor_hardening_01",
    "email": "donor_hardening@bountyloop.org",
    "name": "Hardening Donor Store",
}

MOCK_IDEMP_AUTH = {
    "uid": "fb_donor_idemp_02",
    "email": "donor_idemp@bountyloop.org",
    "name": "Idempotent Donor Store",
}


def _create_jpeg_bytes(width: int = 200, height: int = 200, with_exif: bool = False) -> bytes:
    """Generate in-memory valid JPEG bytes with optional EXIF payload."""
    img = Image.new("RGB", (width, height), color=(220, 120, 50))
    buf = io.BytesIO()

    if with_exif:
        exif = img.getexif()
        # Tags: 0x010e (ImageDescription), 0x0131 (Software)
        exif[0x010E] = "BountyLoop Geotag Lat:30.2672 Lon:-97.7431"
        exif[0x0131] = "BountyLoop Mobile v1.0"
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")

    return buf.getvalue()


# ── 1. Security & Upload Validation Tests ──────────────────────────────────────


def test_magic_bytes_rejects_renamed_text_file() -> None:
    """A .txt file renamed as .jpg must be rejected with HTTP 400."""
    fake_image_bytes = b"This is plain text pretending to be a JPEG image."

    with pytest.raises(HTTPException) as exc_info:
        validate_image_upload(fake_image_bytes, filename="fake_food.jpg", max_upload_mb=10)

    assert exc_info.value.status_code == 400
    assert "magic bytes" in exc_info.value.detail.lower()


def test_oversized_upload_rejected_with_413() -> None:
    """An image exceeding max_upload_mb must be rejected with HTTP 413."""
    valid_jpeg = _create_jpeg_bytes()
    # Artificially test with a 1 KB limit to test cap without allocating 30 MB in memory
    with pytest.raises(HTTPException) as exc_info:
        validate_image_upload(valid_jpeg, filename="large.jpg", max_upload_mb=0)  # 0 MB cap

    assert exc_info.value.status_code == 413
    assert "exceeds maximum permitted upload size" in exc_info.value.detail.lower()


def test_internal_service_token_enforcement() -> None:
    """Verify verify_internal_service_token accepts valid token and rejects invalid."""
    valid_header = f"Bearer {settings.internal_service_token}"
    assert verify_internal_service_token(valid_header) == settings.internal_service_token

    with pytest.raises(HTTPException) as exc1:
        verify_internal_service_token(None)
    assert exc1.value.status_code == 401

    with pytest.raises(HTTPException) as exc2:
        verify_internal_service_token("Bearer wrong-internal-token")
    assert exc2.value.status_code == 403


# ── 2. Privacy & EXIF Stripping Tests ─────────────────────────────────────────


def test_exif_gps_metadata_is_stripped_server_side() -> None:
    """Asserts that EXIF metadata is completely stripped before disk save."""
    raw_with_gps = _create_jpeg_bytes(with_exif=True)
    temp_donation_id = uuid.uuid4()

    rel_path, sha = save_donation_photo(temp_donation_id, raw_with_gps)
    saved_file = Path("storage") / rel_path

    try:
        assert saved_file.exists()
        with Image.open(saved_file) as reloaded_img:
            exif_data = reloaded_img.getexif()
            # Must contain no EXIF tags (clean image)
            assert 0x010E not in exif_data, (
                "EXIF ImageDescription metadata must be completely stripped!"
            )
            assert 0x0131 not in exif_data, "EXIF Software metadata must be completely stripped!"
            assert len(exif_data) == 0, (
                "Saved image container must have zero EXIF metadata dictionaries!"
            )
    finally:
        if saved_file.parent.exists():
            import shutil

            shutil.rmtree(saved_file.parent, ignore_errors=True)


@pytest.mark.asyncio
async def test_privacy_consent_toggle_and_purge_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test user retraining consent toggle and DELETE /v1/me/data Right to be Forgotten."""
    mock_donor = {
        "uid": f"fb_donor_purge_{uuid.uuid4().hex[:8]}",
        "email": f"donor_purge_{uuid.uuid4().hex[:6]}@bountyloop.org",
        "name": "Hardening Purge Donor",
    }
    with patch("app.core.security.verify_firebase_token", return_value=mock_donor):
        headers = {"Authorization": "Bearer test_donor_token"}

        # 1. Update profile with explicit consent
        patch_resp = await client.patch(
            "/v1/me",
            headers=headers,
            json={"consent_model_training": True},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["consent_model_training"] is True

        # 2. Trigger Right to be Forgotten
        purge_resp = await client.delete(
            "/v1/me/data",
            headers=headers,
        )
        assert purge_resp.status_code == 200
        purge_data = purge_resp.json()
        assert purge_data["status"] == "purged"
        assert "retention_policy_link" in purge_data

        # 3. Verify user profile was anonymized in DB
        me_resp = await client.get("/v1/me", headers=headers)
        assert me_resp.status_code == 403
        assert "deactivated" in me_resp.json()["detail"].lower()

        # Direct database query check
        q = select(User).where(User.firebase_uid == mock_donor["uid"])
        purged_user = (await db_session.execute(q)).scalar_one()
        assert purged_user.display_name == "Deleted User"
        assert purged_user.is_active is False
        assert purged_user.consent_model_training is False


# ── 3. Offline Mobile Outbox Idempotency Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_idempotent_donation_submission(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Submitting the same idempotency key twice returns the identical donation without duplicates."""
    idemp_key = f"mobile_offline_{uuid.uuid4()}"
    jpeg_bytes = _create_jpeg_bytes()
    mock_idemp_user = {
        "uid": f"fb_donor_idemp_{uuid.uuid4().hex[:8]}",
        "email": f"donor_idemp_{uuid.uuid4().hex[:6]}@bountyloop.org",
        "name": "Idempotent Donor Store",
    }

    mock_cv = {
        "item": FoodCategory.produce_fruit,
        "item_confidence": 0.95,
        "freshness": FreshnessGrade.grade_2_good,
        "freshness_confidence": 0.92,
        "hazard_flag": HazardFlag.none,
        "hazard_confidence": 0.99,
        "action": "auto_create",
        "needs_review": False,
        "review_reason": None,
        "model_versions": {"item": "item_v1"},
        "latency_ms": 12.0,
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=mock_idemp_user),
        patch(
            "app.services.cv_client.CVClient.predict", new_callable=AsyncMock, return_value=mock_cv
        ),
    ):
        headers = {
            "Authorization": "Bearer test_donor_token",
            "X-Idempotency-Key": idemp_key,
        }

        # First request (simulating initial outbox flush)
        resp1 = await client.post(
            "/v1/donations",
            headers=headers,
            data={"est_weight_kg": "7.5"},
            files=[("files", ("apples.jpg", jpeg_bytes, "image/jpeg"))],
        )
        assert resp1.status_code == 201
        don1 = resp1.json()

        # Second request (simulating network reconnect retry with identical key)
        resp2 = await client.post(
            "/v1/donations",
            headers=headers,
            data={"est_weight_kg": "7.5"},
            files=[("files", ("apples.jpg", jpeg_bytes, "image/jpeg"))],
        )
        assert resp2.status_code == 200
        don2 = resp2.json()

        assert don1["id"] == don2["id"], "Idempotency key must return the existing record!"

        # Assert only ONE record exists in the database
        q = select(func.count(Donation.id)).where(Donation.idempotency_key == idemp_key)
        count = (await db_session.execute(q)).scalar_one()
        assert count == 1, "Exactly one donation record must exist for the idempotency key"


# ── 4. Observability & Health Probes ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_healthz_shallow_and_deep_probes(client: AsyncClient) -> None:
    """Test /healthz liveness and /healthz?deep=true dependency checks."""
    # Shallow probe
    resp_shallow = await client.get("/healthz")
    assert resp_shallow.status_code == 200
    data_shallow = resp_shallow.json()
    assert data_shallow["status"] == "ok"
    assert "version" in data_shallow

    # Deep probe
    resp_deep = await client.get("/healthz?deep=true")
    assert resp_deep.status_code in (200, 503)
    data_deep = resp_deep.json()
    assert "components" in data_deep
    assert "database" in data_deep["components"]
    assert "cv_service" in data_deep["components"]


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient) -> None:
    """Test GET /metrics returns valid standard Prometheus exposition text."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

    content = resp.text
    assert "bountyloop_http_requests_total" in content
    assert "bountyloop_review_queue_depth" in content
    assert "bountyloop_active_offers_count" in content
    assert "bountyloop_impact_kg_rescued_total" in content
    assert "bountyloop_cv_circuit_breaker_state" in content


# ── 5. Resilience: CV Circuit Breaker ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cv_circuit_breaker_degrades_gracefully() -> None:
    """Assert circuit breaker trips to OPEN on repeated failures and provides fallback."""
    cv_circuit_breaker.consecutive_failures = 0
    cv_circuit_breaker.state = "CLOSED"

    # Trip breaker
    cv_circuit_breaker.record_failure()
    cv_circuit_breaker.record_failure()
    cv_circuit_breaker.record_failure()

    assert cv_circuit_breaker.state == "OPEN"
    assert not cv_circuit_breaker.is_available()

    # Call predict() while circuit is open
    fallback = await cv_client.predict(image_bytes=b"dummy", filename="test.jpg")
    assert fallback["needs_review"] is True
    assert fallback["action"] == "human_review_queue"
    assert "circuit_breaker_open" in fallback["model_versions"]["cv_status"]

    # Reset breaker
    cv_circuit_breaker.record_success()
    assert cv_circuit_breaker.state == "CLOSED"


# ── 6. Secret Scan Sanity Check ────────────────────────────────────────────────


def test_no_live_secrets_committed() -> None:
    """Scan tracked repository source files to verify no unencrypted live secrets were committed."""
    project_root = Path(__file__).resolve().parents[2]
    critical_patterns = [
        "AKIA",  # AWS Access Key
        "ghp_",  # GitHub personal token
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ]

    for py_file in project_root.glob("backend/app/**/*.py"):
        text_content = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in critical_patterns:
            assert pattern not in text_content, (
                f"Potential secret pattern '{pattern}' found in {py_file}!"
            )
