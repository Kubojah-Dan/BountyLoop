"""BountyLoop — Authentication, RBAC, and API Skeleton Tests (Phase 2).

Tests:
- RFC-7807 problem+json error formatting on 401, 403, 422.
- Firebase token verification with mocked verifier.
- Automatic user provisioning on first sight (idempotent).
- /auth/session, /me, /me/role contracts.
- Role guard escalation restrictions (donor calling recipient route -> 403).
- OpenAPI documentation availability.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_unauthenticated_request_returns_401_problem_json(client: AsyncClient) -> None:
    """Unauthenticated calls to protected routes must return 401 with application/problem+json."""
    response = await client.get("/v1/me")

    assert response.status_code == 401
    assert "application/problem+json" in response.headers.get("content-type", "")

    body = response.json()
    assert body["status"] == 401
    assert body["title"] == "Unauthorized"
    assert "detail" in body
    assert "type" in body


@pytest.mark.anyio
async def test_invalid_token_returns_401_problem_json(client: AsyncClient) -> None:
    """Invalid bearer tokens must fail verification and return 401 problem+json."""
    headers = {"Authorization": "Bearer invalid_expired_or_forged_token"}
    response = await client.get("/v1/me", headers=headers)

    assert response.status_code == 401
    assert "application/problem+json" in response.headers.get("content-type", "")
    body = response.json()
    assert body["status"] == 401


@pytest.mark.anyio
async def test_validation_error_returns_422_problem_json(client: AsyncClient) -> None:
    """Payload validation failures must return 422 with application/problem+json and invalid_params."""
    # id_token has min_length=10
    response = await client.post("/v1/auth/session", json={"id_token": "short"})

    assert response.status_code == 422
    assert "application/problem+json" in response.headers.get("content-type", "")

    body = response.json()
    assert body["status"] == 422
    assert body["title"] == "Unprocessable Entity"
    assert "invalid_params" in body
    assert len(body["invalid_params"]) > 0


@pytest.mark.anyio
async def test_auth_session_provisions_user_on_first_sight(client: AsyncClient) -> None:
    """Calling /v1/auth/session with valid token must upsert a new user on first sight."""
    mock_uid = f"fb_new_{uuid.uuid4().hex[:8]}"
    mock_email = f"user_{uuid.uuid4().hex[:8]}@bountyloop.org"
    mock_claims: dict[str, Any] = {
        "uid": mock_uid,
        "email": mock_email,
        "name": "Jane Rescuer",
    }

    with (
        patch("app.core.security.verify_firebase_token", return_value=mock_claims),
        patch("app.api.v1.routes.auth.verify_firebase_token", return_value=mock_claims),
    ):
        # 1. First sight — provisions user
        resp1 = await client.post("/v1/auth/session", json={"id_token": "mocked_valid_id_token"})
        assert resp1.status_code == 200
        data1 = resp1.json()

        assert "user_id" in data1
        assert data1["role"] == "donor"  # Default role
        assert data1["profile"]["email"] == mock_email
        assert data1["profile"]["display_name"] == "Jane Rescuer"

        # 2. Second call — idempotent; same user returned
        resp2 = await client.post("/v1/auth/session", json={"id_token": "mocked_valid_id_token"})
        assert resp2.status_code == 200
        data2 = resp2.json()

        assert data2["user_id"] == data1["user_id"]
        assert data2["profile"]["id"] == data1["profile"]["id"]


@pytest.mark.anyio
async def test_get_me_and_patch_me(client: AsyncClient) -> None:
    """Authenticated user can read and update their profile via /v1/me."""
    mock_uid = f"fb_patch_{uuid.uuid4().hex[:8]}"
    mock_email = f"patch_{uuid.uuid4().hex[:8]}@bountyloop.org"
    mock_claims: dict[str, Any] = {
        "uid": mock_uid,
        "email": mock_email,
        "name": "Original Name",
    }

    with patch("app.core.security.verify_firebase_token", return_value=mock_claims):
        headers = {"Authorization": "Bearer mock_token_for_patch"}

        # Read /me
        get_resp = await client.get("/v1/me", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["display_name"] == "Original Name"

        # Update /me
        patch_resp = await client.patch(
            "/v1/me",
            headers=headers,
            json={
                "display_name": "Updated Name",
                "phone_e164": "+15125557777",
                "org_name": "Green Earth Grocers",
            },
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["display_name"] == "Updated Name"
        assert patch_data["phone_e164"] == "+15125557777"
        assert patch_data["org_name"] == "Green Earth Grocers"


@pytest.mark.anyio
async def test_update_my_role_onboarding(client: AsyncClient) -> None:
    """Onboarding endpoint /v1/me/role allows setting user role and organization name."""
    mock_uid = f"fb_role_{uuid.uuid4().hex[:8]}"
    mock_email = f"role_{uuid.uuid4().hex[:8]}@bountyloop.org"
    mock_claims: dict[str, Any] = {
        "uid": mock_uid,
        "email": mock_email,
        "name": "Food Pantry Volunteer",
    }

    with patch("app.core.security.verify_firebase_token", return_value=mock_claims):
        headers = {"Authorization": "Bearer mock_token_for_role"}

        resp = await client.post(
            "/v1/me/role",
            headers=headers,
            json={"role": "recipient", "org_name": "Hope Community Pantry"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "recipient"
        assert data["org_name"] == "Hope Community Pantry"


@pytest.mark.anyio
async def test_role_guards_enforce_rbac(client: AsyncClient) -> None:
    """Role guards must allow permitted roles and reject forbidden roles with 403."""
    mock_uid = f"fb_guard_{uuid.uuid4().hex[:8]}"
    mock_email = f"guard_{uuid.uuid4().hex[:8]}@bountyloop.org"
    mock_claims: dict[str, Any] = {
        "uid": mock_uid,
        "email": mock_email,
        "name": "Strict Donor",
    }

    with patch("app.core.security.verify_firebase_token", return_value=mock_claims):
        headers = {"Authorization": "Bearer mock_token_guard"}

        # Default role is donor
        # 1. Calling donor route succeeds
        donor_resp = await client.get("/v1/role-guard/donor-only", headers=headers)
        assert donor_resp.status_code == 200
        assert "Welcome donor" in donor_resp.json()["message"]

        # 2. Calling recipient route fails with 403 problem+json
        recip_resp = await client.get("/v1/role-guard/recipient-only", headers=headers)
        assert recip_resp.status_code == 403
        assert "application/problem+json" in recip_resp.headers.get("content-type", "")
        body = recip_resp.json()
        assert body["status"] == 403
        assert body["title"] == "Forbidden"
        assert "recipient" in body["detail"]

        # 3. Calling admin route fails with 403 problem+json
        admin_resp = await client.get("/v1/role-guard/admin-only", headers=headers)
        assert admin_resp.status_code == 403
        assert admin_resp.json()["status"] == 403


@pytest.mark.anyio
async def test_openapi_docs_available(client: AsyncClient) -> None:
    """OpenAPI documentation and specification must be accessible."""
    docs_resp = await client.get("/docs")
    assert docs_resp.status_code == 200

    schema_resp = await client.get("/openapi.json")
    assert schema_resp.status_code == 200
    schema = schema_resp.json()
    assert "/v1/auth/session" in schema["paths"]
    assert "/v1/me" in schema["paths"]
    assert "/v1/me/role" in schema["paths"]
