"""BountyLoop — Unit Tests for Impact Calculations (meals, CO2e)."""

from __future__ import annotations

import pytest

from app.services.impact import (
    co2e_avoided,
    compute_donation_impact,
    meals_equivalent,
)


def test_meals_equivalent_default_factor() -> None:
    """12 kg rescued at 1.2 kg/meal yields exactly 10.0 meals."""
    assert meals_equivalent(12.0) == 10.0
    assert meals_equivalent(6.0) == 5.0
    assert meals_equivalent(1.8) == 1.5


def test_co2e_avoided_default_factor() -> None:
    """10 kg rescued at 2.5 kg CO2e/kg yields 25.0 kg CO2e avoided."""
    assert co2e_avoided(10.0) == 25.0
    assert co2e_avoided(4.2) == 10.50


def test_compute_donation_impact_payload() -> None:
    """compute_donation_impact outputs complete structured impact dictionary."""
    impact = compute_donation_impact(15.0)
    assert impact["kg_rescued"] == 15.0
    assert impact["meals_equivalent"] == 12.5
    assert impact["co2e_avoided_kg"] == 37.5
    assert impact["method_version"] == "v1"


def test_invalid_factors_raise_error() -> None:
    """Non-positive meal factor or negative CO2e factor raises ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        meals_equivalent(10.0, factor=0.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        co2e_avoided(10.0, factor=-1.0)
