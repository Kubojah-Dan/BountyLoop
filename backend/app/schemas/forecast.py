"""BountyLoop — Pydantic schemas for Surplus Forecasting (Phase 11)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field


class DonorForecastDay(BaseModel):
    """Single day predicted surplus for a donor."""

    date: datetime.date
    predicted_kg: float
    confidence_lower_kg: float | None = None
    confidence_upper_kg: float | None = None
    model_version: str = "sarimax_v1"
    is_synthetic: bool = True


class DonorForecastRead(BaseModel):
    """7-day forward surplus forecast for a specific donor."""

    donor_id: uuid.UUID
    donor_name: str
    forecasts: list[DonorForecastDay]
    total_predicted_kg: float
    generated_at: datetime.datetime
    is_synthetic: bool = True
    methodology_note: str = (
        "Surplus forecasts are modeled planning estimates for route and volunteer optimization. "
        "All values are marked synthetic until 8+ weeks of empirical pilot data are collected."
    )


class AggregateForecastDay(BaseModel):
    """Aggregated community surplus forecast for a single date."""

    date: datetime.date
    total_predicted_kg: float
    active_donors_count: int
    is_synthetic: bool = True


class AggregateForecastRead(BaseModel):
    """Aggregated multi-donor community surplus forecast."""

    start_date: datetime.date
    end_date: datetime.date
    forecast_days: list[AggregateForecastDay]
    total_projected_surplus_kg: float
    is_synthetic: bool = True
    disclaimer: str = (
        "Aggregate forecasts provide operational routing guidance for rescue coordinators. "
        "Modeled synthetic projections; does not constitute a guaranteed food inventory."
    )


class ForecastGenerateRequest(BaseModel):
    """Request payload to trigger forecast generation."""

    donor_ids: list[uuid.UUID] | None = None
    horizon_days: int = Field(default=7, ge=1, le=30)
    model_version: str = "sarimax_v1"


class ForecastGenerateResponse(BaseModel):
    """Result of batch forecast generation."""

    status: str
    forecasts_generated: int
    donors_count: int
    model_version: str
    is_synthetic: bool = True


class ForecastMetricsItem(BaseModel):
    """Performance evaluation record for a forecasting model."""

    model_name: str
    mae: float
    rmse: float
    mape: float
    num_eval_points: int
    beats_baseline: bool
    is_synthetic: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForecastBenchmarkResponse(BaseModel):
    """Benchmark report comparing models across walk-forward validation."""

    dataset_type: str = "SYNTHETIC_TIME_SERIES"
    eval_strategy: str = "Rolling Walk-Forward (7-day horizon, no future leakage)"
    baseline_model: str = "naive_seasonal_baseline"
    metrics: list[ForecastMetricsItem]
    disclaimer: str = (
        "Benchmarked on synthetic per-donor daily surplus time series. "
        "Production deployment requires retraining on >= 8 weeks of real pilot logs."
    )


class ForecastPromptTriggerRequest(BaseModel):
    """Request to evaluate and dispatch evening surplus prompts to donors."""

    min_predicted_kg: float = Field(default=5.0, ge=0.0)
    target_date: datetime.date | None = None


class ForecastPromptTriggerResponse(BaseModel):
    """Status of donor reminder prompt dispatch."""

    prompts_enabled: bool
    prompts_dispatched: int
    details: list[dict[str, Any]]
    message: str
