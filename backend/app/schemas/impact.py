"""BountyLoop — Impact Measurement Schemas.

Pydantic models for environmental and social impact summaries, timeseries,
reconciliation audits, and methodology transparency metadata (§6 Phase 10).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImpactFactorDetail(BaseModel):
    """Metadata and provenance citation for an impact calculation factor."""

    factor_name: str
    value: float
    unit: str
    source: str
    status: str  # "verified_standard", "unverified_estimate", "verified_empirical"
    description: str


class ImpactMethodologyRead(BaseModel):
    """Methodology documentation, citation provenance, and transparency disclosures."""

    version: str = "v1.0"
    meal_kg_factor: ImpactFactorDetail
    co2e_factor: ImpactFactorDetail
    disclaimer: str = Field(
        default="CO2e avoided is a modeled estimate based on landfill diversion factors (EPA WARM / UNEP). It is not laboratory-measured.",
        description="Scientific honesty disclosure for carbon impact metrics.",
    )


class ImpactSummaryRead(BaseModel):
    """Aggregated environmental and social impact summary metrics."""

    total_donations_rescued: int = Field(
        ..., ge=0, description="Total completed food rescue transactions"
    )
    total_kg_rescued: float = Field(
        ..., ge=0.0, description="Empirically verified surplus food weight in kg"
    )
    total_meals_equivalent: float = Field(
        ..., ge=0.0, description="Standard meal equivalents (1.2 kg/meal)"
    )
    total_co2e_avoided_kg: float = Field(
        ..., ge=0.0, description="Modeled GHG emissions avoided in kg CO2e"
    )
    co2e_is_estimate: bool = Field(
        default=True, description="Always true; flags carbon avoidance as modeled estimate"
    )
    method_version: str = "v1.0"
    disclaimer: str = (
        "Greenhouse gas emissions avoided are modeled estimates based on landfill diversion. "
        "Not laboratory-measured."
    )
    factors: dict[str, Any] = Field(default_factory=dict)


class ImpactTimeseriesPoint(BaseModel):
    """Impact metrics aggregated within a specific temporal bucket (day, week, month)."""

    period: str = Field(..., description="Date or period identifier, e.g. '2026-11-01'")
    donations_count: int = Field(..., ge=0)
    kg_rescued: float = Field(..., ge=0.0)
    meals_equivalent: float = Field(..., ge=0.0)
    co2e_avoided_kg: float = Field(..., ge=0.0)
    co2e_is_estimate: bool = True


class ImpactTimeseriesRead(BaseModel):
    """Timeseries collection of historical impact metrics with summary totals."""

    interval: str = Field(..., description="Aggregation frequency: 'day', 'week', or 'month'")
    points: list[ImpactTimeseriesPoint]
    summary: ImpactSummaryRead


class ImpactReconciliationRead(BaseModel):
    """Database reconciliation audit comparing completed claims, donations, and impact_log rows."""

    reconciled: bool = Field(
        ..., description="True if completed records and impact logs match 1:1 with zero delta"
    )
    completed_claims_count: int
    completed_donations_count: int
    impact_rows_count: int
    total_donation_weight_kg: float
    total_impact_kg_rescued: float
    weight_delta_kg: float
    discrepancies: list[str] = Field(default_factory=list)
