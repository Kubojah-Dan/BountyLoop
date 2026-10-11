"""BountyLoop — Tests for POST /predict (ONNX inference, error cases, latency budget)."""

from __future__ import annotations

import io
import time

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient
from PIL import Image


def create_test_image(
    width: int = 224, height: int = 224, color=(200, 50, 50)
) -> bytes:
    """Generate in-memory JPEG bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_predict_happy_path_returns_prediction() -> None:
    """Valid image returns 200 with complete classification and safety schema."""
    image_bytes = create_test_image()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/predict",
            files={"file": ("apple.jpg", image_bytes, "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()

    assert "item" in data
    assert "item_confidence" in data
    assert "freshness" in data
    assert data["freshness"] in ["fresh", "spoiled"]
    assert "freshness_confidence" in data
    assert 0.0 <= data["freshness_confidence"] <= 1.0
    assert "hazard_flag" in data
    assert "needs_review" in data
    assert isinstance(data["needs_review"], bool)
    assert "latency_ms" in data
    assert data["latency_ms"] > 0


@pytest.mark.asyncio
async def test_predict_latency_under_500ms_budget() -> None:
    """Inference latency on CPU must meet the p95 < 500 ms target."""
    image_bytes = create_test_image()
    latencies: list[float] = []

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(5):
            t0 = time.perf_counter()
            resp = await client.post(
                "/predict",
                files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200
            latencies.append(elapsed_ms)

    # 95th percentile check
    latencies.sort()
    p95 = latencies[-1]
    assert p95 < 500.0, f"p95 latency {p95:.2f}ms exceeded 500ms budget"


@pytest.mark.asyncio
async def test_predict_empty_file_returns_400_problem_json() -> None:
    """Empty file returns 400 Bad Request with RFC-7807 problem+json."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/predict",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
    assert resp.status_code == 400
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 400
    assert data["title"] == "Bad Request"
    assert "Empty" in data["detail"]


@pytest.mark.asyncio
async def test_predict_non_image_bytes_returns_400_problem_json() -> None:
    """Non-image corrupt bytes returns 400 Bad Request."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/predict",
            files={
                "file": ("corrupt.jpg", b"NOT_A_VALID_IMAGE_HEADER_DATA", "image/jpeg")
            },
        )
    assert resp.status_code == 400
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 400
    assert "Unreadable" in data["detail"] or "unsupported" in data["detail"]


@pytest.mark.asyncio
async def test_predict_oversized_file_returns_413_problem_json() -> None:
    """Upload exceeding 10MB limit returns 413 Payload Too Large."""
    # 10.5 MB payload
    oversized_bytes = b"0" * (11 * 1024 * 1024)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/predict",
            files={"file": ("huge.jpg", oversized_bytes, "image/jpeg")},
        )
    assert resp.status_code == 413
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 413
    assert data["title"] == "Payload Too Large"
