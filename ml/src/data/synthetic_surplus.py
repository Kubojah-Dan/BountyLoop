"""BountyLoop — Synthetic Surplus Time Series Generator.

================================================================================
CRITICAL ETHICAL & SCIENTIFIC NOTICE:
ALL DATA PRODUCED BY THIS MODULE IS STRICTLY SYNTHETIC AND ARTIFICIALLY GENERATED.
IT MUST NEVER BE PRESENTED AS EMPIRICAL RESCUE RECORDS, OBSERVED AUDIT DATA,
OR REAL FOOD WASTE STREAMS.
================================================================================

This module generates multi-donor daily surplus time series for training and
benchmarking time series forecasting models (SARIMAX and LightGBM).

Features modeled:
- Donor-specific baseline surplus scale (e.g. bakeries vs. supermarkets vs. restaurants).
- Weekly seasonality (weekday vs. weekend patterns, Friday/Saturday restaurant surges).
- Annual / monthly seasonality (temperature sinusoid).
- Local holiday shocks (demand shifts before and after holidays).
- Weather covariates (temperature in °C, precipitation in mm).
- Stochastic multiplicative log-normal noise ensuring strictly non-negative values.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DonorProfile:
    """Configures baseline surplus behavior for a donor archetype."""

    donor_type: str
    base_kg: float
    weekend_factor: float
    friday_factor: float
    holiday_spike: float
    weather_sensitivity: float  # sensitivity to rain/heat
    noise_sigma: float


DEFAULT_PROFILES: dict[str, DonorProfile] = {
    "supermarket": DonorProfile(
        donor_type="supermarket",
        base_kg=45.0,
        weekend_factor=1.45,
        friday_factor=1.30,
        holiday_spike=1.60,
        weather_sensitivity=0.15,
        noise_sigma=0.18,
    ),
    "bakery": DonorProfile(
        donor_type="bakery",
        base_kg=18.0,
        weekend_factor=1.35,
        friday_factor=1.20,
        holiday_spike=1.40,
        weather_sensitivity=0.08,
        noise_sigma=0.15,
    ),
    "restaurant": DonorProfile(
        donor_type="restaurant",
        base_kg=22.0,
        weekend_factor=1.55,
        friday_factor=1.40,
        holiday_spike=1.50,
        weather_sensitivity=0.20,
        noise_sigma=0.22,
    ),
    "cafe": DonorProfile(
        donor_type="cafe",
        base_kg=8.5,
        weekend_factor=1.25,
        friday_factor=1.15,
        holiday_spike=1.25,
        weather_sensitivity=0.10,
        noise_sigma=0.14,
    ),
    "caterer": DonorProfile(
        donor_type="caterer",
        base_kg=35.0,
        weekend_factor=1.70,
        friday_factor=1.50,
        holiday_spike=1.80,
        weather_sensitivity=0.25,
        noise_sigma=0.30,
    ),
}


def generate_synthetic_weather(
    dates: pd.DatetimeIndex,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate daily temperature (°C) and precipitation (mm)."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    day_of_year = dates.dayofyear.to_numpy()

    # Temperature: seasonal sinusoid (15°C mean, 10°C amplitude) + noise
    temp_seasonal = 15.0 + 10.0 * np.sin(2.0 * np.pi * (day_of_year - 80) / 365.25)
    temp_noise = rng.normal(0, 2.5, size=n)
    temperatures = np.round(temp_seasonal + temp_noise, 1)

    # Precipitation: zero-inflated Gamma (p_rain ~ 0.25)
    rain_mask = rng.binomial(1, 0.25, size=n).astype(bool)
    rain_amounts = np.zeros(n)
    if rain_mask.any():
        rain_amounts[rain_mask] = rng.gamma(shape=2.0, scale=3.5, size=rain_mask.sum())
    precipitation = np.round(rain_amounts, 1)

    return pd.DataFrame(
        {
            "temperature_c": temperatures,
            "precipitation_mm": precipitation,
        },
        index=dates,
    )


def simulate_donor_time_series(
    donor_id: str,
    donor_name: str,
    donor_type: str,
    start_date: datetime.date = datetime.date(2025, 1, 1),
    num_days: int = 365,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate daily surplus time series for a single donor.

    Returns a DataFrame with explicit `is_synthetic=True` column and all
    relevant calendar and weather covariates.
    """
    profile = DEFAULT_PROFILES.get(donor_type, DEFAULT_PROFILES["supermarket"])
    dates = pd.date_range(start=start_date, periods=num_days, freq="D")
    rng = np.random.default_rng(seed)

    weather_df = generate_synthetic_weather(dates, seed=seed)

    records: list[dict[str, Any]] = []

    # Known fixed holidays (month, day)
    holidays = {(1, 1), (5, 1), (7, 4), (11, 27), (12, 24), (12, 25), (12, 31)}

    for i, dt in enumerate(dates):
        dow = dt.weekday()  # 0=Monday, 6=Sunday
        is_weekend = dow in (5, 6)
        is_friday = dow == 4
        is_holiday = (dt.month, dt.day) in holidays

        # Base multiplier
        mult = 1.0

        if is_weekend:
            mult *= profile.weekend_factor
        elif is_friday:
            mult *= profile.friday_factor

        if is_holiday:
            mult *= profile.holiday_spike

        # Weather influence: heavy rain reduces foot traffic in cafes/restaurants,
        # but can cause supermarket overstock.
        rain = weather_df.iloc[i]["precipitation_mm"]
        if rain > 5.0:
            rain_effect = 1.0 + (profile.weather_sensitivity * min(rain / 20.0, 1.5))
            mult *= rain_effect

        # Lognormal multiplicative noise
        noise = rng.lognormal(mean=0.0, sigma=profile.noise_sigma)
        surplus_kg = round(max(0.0, profile.base_kg * mult * noise), 2)

        records.append(
            {
                "donor_id": donor_id,
                "donor_name": donor_name,
                "donor_type": donor_type,
                "date": dt.date(),
                "surplus_kg": surplus_kg,
                "day_of_week": dow,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "temperature_c": weather_df.iloc[i]["temperature_c"],
                "precipitation_mm": rain,
                "is_synthetic": True,
                "data_provenance": "SYNTHETIC_GENERATOR_V1",
            }
        )

    df = pd.DataFrame(records)
    return df


def generate_multi_donor_dataset(
    start_date: datetime.date = datetime.date(2025, 1, 1),
    num_days: int = 365,
    seed: int = 100,
) -> pd.DataFrame:
    """Generate a combined synthetic dataset across canonical donor archetypes."""
    donors = [
        ("00000000-0000-0000-0000-000000000001", "Daily Harvest Bakery", "bakery"),
        (
            "00000000-0000-0000-0000-000000000002",
            "Green Valley Supermarket",
            "supermarket",
        ),
        ("00000000-0000-0000-0000-000000000003", "Trattoria Bella", "restaurant"),
        ("00000000-0000-0000-0000-000000000004", "Bean & Leaf Cafe", "cafe"),
        ("00000000-0000-0000-0000-000000000005", "Summit Event Catering", "caterer"),
    ]

    all_dfs = []
    for i, (d_id, name, d_type) in enumerate(donors):
        df_donor = simulate_donor_time_series(
            donor_id=d_id,
            donor_name=name,
            donor_type=d_type,
            start_date=start_date,
            num_days=num_days,
            seed=seed + i * 17,
        )
        all_dfs.append(df_donor)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df


if __name__ == "__main__":
    df = generate_multi_donor_dataset(num_days=180, seed=42)
    print(
        f"Generated {len(df)} synthetic daily surplus records for {df['donor_id'].nunique()} donors."
    )
    print(df.head(10))
