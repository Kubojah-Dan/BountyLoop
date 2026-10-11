"""Phase 0: CV service health endpoint tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_cv_healthz_returns_200() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_cv_predict_stub_returns_501() -> None:
    """Phase 0: /predict must return 501 Not Implemented (stub until Phase 3)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/predict",
            files={"file": ("test.jpg", b"fake-image-data", "image/jpeg")},
        )
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_cv_models_endpoint() -> None:
    """Phase 0: /models returns empty dict (no models loaded yet)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/models")
    assert response.status_code == 200
    assert response.json()["models"] == {}
