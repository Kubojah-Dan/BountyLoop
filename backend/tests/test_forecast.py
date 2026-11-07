"""BountyLoop — Backend Test Suite for Surplus Forecasting Service & API (Phase 11).

Tests:
1. Database persistence and single-slot idempotency (donor_surplus_forecasts table).
2. Service layer (generate_donor_forecasts, get_donor_forecast, get_aggregate_forecast, batch generation).
3. Forecast API routes (/v1/forecast/donor/{id}, /v1/forecast/aggregate, /v1/forecast/metrics).
4. Feature flag toggling for donor reminder prompts (FORECAST_PROMPTS_ENABLED).
5. Agent routing tool integration (tool_query_surplus_forecast).
"""

from __future__ import annotations

import datetime
import uuid

import pytest
from geoalchemy2.elements import WKTElement
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import tool_query_surplus_forecast
from app.core.config import get_settings
from app.db.models import Donor, DonorKind, DonorSurplusForecast, User, UserRole
from app.services.forecast import (
    generate_batch_forecasts,
    generate_donor_forecasts,
    get_aggregate_forecast,
    get_donor_forecast,
    trigger_forecast_prompts,
)

settings = get_settings()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def sample_donor(db_session: AsyncSession) -> Donor:
    """Create a sample donor for forecasting tests."""
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_donor_{uuid.uuid4().hex[:8]}",
        email=f"donor_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.donor,
        display_name="Artisan Sourdough Bakery",
        org_name="Artisan Sourdough Bakery",
        phone_e164="+15551234567",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    donor = Donor(
        id=uuid.uuid4(),
        user_id=user.id,
        kind=DonorKind.grocery,
        address="104 Commercial St, Food District",
        location=WKTElement("POINT(-97.7431 30.2672)", srid=4326),
    )
    db_session.add(donor)
    await db_session.commit()
    await db_session.refresh(donor)
    return donor


# ── 1. Database & Service Layer Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_and_get_donor_forecast(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify generating donor forecasts persists rows and returns 7-day forecast."""
    forecasts = await generate_donor_forecasts(
        db=db_session,
        donor=sample_donor,
        horizon_days=7,
        model_version="sarimax_v1",
    )
    assert len(forecasts) == 7
    assert all(f.is_synthetic for f in forecasts)
    assert all(f.predicted_kg > 0 for f in forecasts)

    # Check persistence in DB
    q = select(DonorSurplusForecast).where(DonorSurplusForecast.donor_id == sample_donor.id)
    saved = (await db_session.execute(q)).scalars().all()
    assert len(saved) == 7

    # Retrieve via service
    read_obj = await get_donor_forecast(db=db_session, donor_id=sample_donor.id, horizon_days=7)
    assert read_obj is not None
    assert read_obj.donor_id == sample_donor.id
    assert len(read_obj.forecasts) == 7
    assert read_obj.total_predicted_kg > 0
    assert read_obj.is_synthetic is True


@pytest.mark.asyncio
async def test_donor_forecast_idempotency_upsert(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify repeated forecast generation does not duplicate rows."""
    await generate_donor_forecasts(db=db_session, donor=sample_donor, horizon_days=7)
    # Re-run same forecast
    await generate_donor_forecasts(db=db_session, donor=sample_donor, horizon_days=7)

    q = select(DonorSurplusForecast).where(DonorSurplusForecast.donor_id == sample_donor.id)
    saved = (await db_session.execute(q)).scalars().all()
    assert len(saved) == 7, "Must maintain exactly 7 rows per donor horizon without duplicates"


@pytest.mark.asyncio
async def test_aggregate_community_forecast(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify community aggregate sums predicted weights across active donors."""
    agg = await get_aggregate_forecast(db=db_session, horizon_days=7)
    assert len(agg.forecast_days) == 7
    assert agg.total_projected_surplus_kg > 0.0
    assert agg.is_synthetic is True


@pytest.mark.asyncio
async def test_batch_forecast_generation(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify batch generator handles multiple donors."""
    res = await generate_batch_forecasts(
        db=db_session,
        donor_ids=[sample_donor.id],
        horizon_days=7,
    )
    assert res.status == "success"
    assert res.donors_count == 1
    assert res.forecasts_generated == 7
    assert res.is_synthetic is True


# ── 2. Feature Flag & Prompt Reminder Tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_forecast_prompts_gated_when_disabled(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify reminder prompts return a safe no-op when FORECAST_PROMPTS_ENABLED=False."""
    settings.forecast_prompts_enabled = False

    resp = await trigger_forecast_prompts(
        db=db_session,
        min_predicted_kg=5.0,
    )
    assert resp.prompts_enabled is False
    assert resp.prompts_dispatched == 0
    assert "disabled" in resp.message.lower()


@pytest.mark.asyncio
async def test_forecast_prompts_dispatch_when_enabled(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify reminder prompts queue messages when FORECAST_PROMPTS_ENABLED=True."""
    settings.forecast_prompts_enabled = True

    try:
        # Generate forecasts first
        await generate_donor_forecasts(db=db_session, donor=sample_donor, horizon_days=3)

        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        resp = await trigger_forecast_prompts(
            db=db_session,
            min_predicted_kg=1.0,
            target_date=tomorrow,
        )

        assert resp.prompts_enabled is True
        assert resp.prompts_dispatched >= 1
        assert len(resp.details) >= 1
        assert "Tomorrow looks like a surplus day" in resp.details[0]["prompt_message"]
    finally:
        # Revert feature flag to default False
        settings.forecast_prompts_enabled = False


# ── 3. Agent Routing Tool Integration Tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_agent_tool_query_surplus_forecast(
    db_session: AsyncSession,
    sample_donor: Donor,
) -> None:
    """Verify agent's tool_query_surplus_forecast returns structured planning hint."""
    hint = await tool_query_surplus_forecast(
        donor_id=sample_donor.id,
        horizon_days=7,
        db=db_session,
    )

    assert "error" not in hint
    assert hint["donor_id"] == str(sample_donor.id)
    assert hint["total_predicted_kg"] > 0
    assert hint["is_synthetic"] is True
    assert "operational_hint" in hint
    assert "planning only" in hint["operational_hint"].lower()


# ── 4. API Route Integration Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_get_donor_forecast(
    client: AsyncClient,
    sample_donor: Donor,
) -> None:
    """Test GET /v1/forecast/donor/{donor_id} returns 200 with forecast payload."""
    resp = await client.get(f"/v1/forecast/donor/{sample_donor.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["donor_id"] == str(sample_donor.id)
    assert len(data["forecasts"]) == 7
    assert data["total_predicted_kg"] > 0
    assert data["is_synthetic"] is True
    assert "methodology_note" in data


@pytest.mark.asyncio
async def test_api_get_donor_forecast_404_for_unknown(
    client: AsyncClient,
) -> None:
    """Test GET /v1/forecast/donor/{unknown_id} returns 404."""
    random_id = uuid.uuid4()
    resp = await client.get(f"/v1/forecast/donor/{random_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_get_aggregate_forecast(
    client: AsyncClient,
    sample_donor: Donor,
) -> None:
    """Test GET /v1/forecast/aggregate returns community predictions."""
    resp = await client.get("/v1/forecast/aggregate")
    assert resp.status_code == 200
    data = resp.json()

    assert "forecast_days" in data
    assert len(data["forecast_days"]) == 7
    assert data["is_synthetic"] is True
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_api_get_metrics_benchmark(
    client: AsyncClient,
) -> None:
    """Test GET /v1/forecast/metrics returns walk-forward benchmark records."""
    resp = await client.get("/v1/forecast/metrics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["dataset_type"] == "SYNTHETIC_TIME_SERIES"
    assert "walk-forward" in data["eval_strategy"].lower()
    assert len(data["metrics"]) == 3

    model_names = [m["model_name"] for m in data["metrics"]]
    assert "naive_seasonal_baseline" in model_names
    assert "sarimax_v1" in model_names
    assert "lightgbm_v1" in model_names


@pytest.mark.asyncio
async def test_api_trigger_prompts_feature_flag(
    client: AsyncClient,
) -> None:
    """Test POST /v1/forecast/prompts/trigger respects feature flag."""
    resp = await client.post(
        "/v1/forecast/prompts/trigger",
        json={"min_predicted_kg": 5.0},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Default is False
    assert data["prompts_enabled"] is False
    assert data["prompts_dispatched"] == 0
