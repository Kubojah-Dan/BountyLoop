"""BountyLoop — Environmental & Social Impact Calculation Service.

Pure functions implementing defensible surplus rescue metrics:
- meals_equivalent: kg / MEAL_KG_FACTOR (default 1.2 kg per meal equivalent;
  reference: USDA Economic Research Service / ReFED food redistribution conversion standard).
- co2e_avoided: kg * IMPACT_CO2E_FACTOR (default 2.5 kg CO2e per kg food waste avoided;
  reference: UNEP Food Waste Index / EPA Waste Reduction Model [WARM], marked UNVERIFIED estimate).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

IMPACT_METHOD_VERSION = "v1"


def meals_equivalent(weight_kg: float, factor: float | None = None) -> float:
    """Calculate meal equivalents from rescued food weight.

    Methodology:
    Conversion factor is configurable via MEAL_KG_FACTOR (default 1.2 kg/meal).
    Reference: USDA Food Loss and Waste metrics / ReFED surplus food redistribution guidelines.
    """
    if factor is None:
        factor = get_settings().meal_kg_factor
    if factor <= 0:
        raise ValueError("Meal conversion factor must be strictly positive.")
    return round(float(weight_kg) / factor, 1)


def co2e_avoided(weight_kg: float, factor: float | None = None) -> float:
    """Calculate greenhouse gas emissions avoided in kg CO2e.

    Methodology:
    Conversion factor is configurable via IMPACT_CO2E_FACTOR (default 2.5 kg CO2e/kg).
    Citation: Derived from EPA WARM (Waste Reduction Model) and UNEP Food Waste Index reports.
    Status: UNVERIFIED estimate (peer-reviewed verification pending in pilot operations).
    """
    if factor is None:
        factor = get_settings().impact_co2e_factor
    if factor < 0:
        raise ValueError("CO2e factor cannot be negative.")
    return round(float(weight_kg) * factor, 2)


def compute_donation_impact(
    weight_kg: float,
    meal_factor: float | None = None,
    co2e_factor: float | None = None,
) -> dict[str, Any]:
    """Compute complete impact payload for a given weight in kg."""
    meals = meals_equivalent(weight_kg, factor=meal_factor)
    co2e = co2e_avoided(weight_kg, factor=co2e_factor)
    return {
        "kg_rescued": round(float(weight_kg), 2),
        "meals_equivalent": meals,
        "co2e_avoided_kg": co2e,
        "method_version": IMPACT_METHOD_VERSION,
    }
