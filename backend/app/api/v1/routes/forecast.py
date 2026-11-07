"""BountyLoop — Surplus Forecasting API Routes (Phase 11).

Endpoints:
- GET  /v1/forecast/donor/{donor_id} : 7-day forward surplus prediction for a donor.
- GET  /v1/forecast/aggregate        : Community-wide aggregate daily surplus projections.
- POST /v1/forecast/generate         : Batch forecast generator for active donors.
- GET  /v1/forecast/metrics          : Walk-forward cross-validation benchmark results.
- POST /v1/forecast/prompts/trigger  : Donor surplus reminder trigger (gated by FORECAST_PROMPTS_ENABLED).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.forecast import (
    AggregateForecastRead,
    DonorForecastRead,
    ForecastBenchmarkResponse,
    ForecastGenerateRequest,
    ForecastGenerateResponse,
    ForecastPromptTriggerRequest,
    ForecastPromptTriggerResponse,
)
from app.services.forecast import (
    generate_batch_forecasts,
    get_aggregate_forecast,
    get_donor_forecast,
    get_forecast_benchmark_metrics,
    trigger_forecast_prompts,
)

router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.get(
    "/donor/{donor_id}",
    response_model=DonorForecastRead,
    summary="Get 7-day surplus forecast for a donor",
)
async def get_donor_surplus_forecast(
    donor_id: uuid.UUID,
    horizon_days: int = Query(7, ge=1, le=30, description="Forecast horizon in days"),
    model_version: str = Query("sarimax_v1", description="Forecasting model version"),
    db: AsyncSession = Depends(get_db),
) -> DonorForecastRead:
    """Retrieve forward surplus projections for a specific donor."""
    forecast = await get_donor_forecast(
        db=db,
        donor_id=donor_id,
        horizon_days=horizon_days,
        model_version=model_version,
    )
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donor with ID {donor_id} not found",
        )
    return forecast


@router.get(
    "/aggregate",
    response_model=AggregateForecastRead,
    summary="Get community-wide aggregate surplus forecast",
)
async def get_community_aggregate_forecast(
    horizon_days: int = Query(7, ge=1, le=30, description="Forecast horizon in days"),
    model_version: str = Query("sarimax_v1", description="Forecasting model version"),
    db: AsyncSession = Depends(get_db),
) -> AggregateForecastRead:
    """Retrieve community-wide daily surplus projections across all donors."""
    return await get_aggregate_forecast(
        db=db,
        horizon_days=horizon_days,
        model_version=model_version,
    )


@router.post(
    "/generate",
    response_model=ForecastGenerateResponse,
    summary="Generate batch forecasts for active donors",
)
async def generate_batch_surplus_forecasts(
    payload: ForecastGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ForecastGenerateResponse:
    """Generate or refresh multi-day forecasts for donors."""
    return await generate_batch_forecasts(
        db=db,
        donor_ids=payload.donor_ids,
        horizon_days=payload.horizon_days,
        model_version=payload.model_version,
    )


@router.get(
    "/metrics",
    response_model=ForecastBenchmarkResponse,
    summary="Get walk-forward cross-validation metrics",
)
async def get_walk_forward_metrics() -> ForecastBenchmarkResponse:
    """Retrieve walk-forward evaluation comparison (Naive vs SARIMAX vs LightGBM)."""
    return get_forecast_benchmark_metrics()


@router.post(
    "/prompts/trigger",
    response_model=ForecastPromptTriggerResponse,
    summary="Trigger evening surplus reminder prompts to donors",
)
async def trigger_surplus_prompts(
    payload: ForecastPromptTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> ForecastPromptTriggerResponse:
    """Evaluate predicted surplus and dispatch evening reminder prompts to donors.

    Gated by the FORECAST_PROMPTS_ENABLED feature flag.
    When disabled, safely returns a no-op response with zero side effects.
    """
    return await trigger_forecast_prompts(
        db=db,
        min_predicted_kg=payload.min_predicted_kg,
        target_date=payload.target_date,
    )
