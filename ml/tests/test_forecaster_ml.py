"""BountyLoop — Tests for Synthetic Data Generation and ML Forecaster Models (Phase 11)."""

from __future__ import annotations

from ml.src.data.synthetic_surplus import (
    DEFAULT_PROFILES,
    generate_multi_donor_dataset,
    simulate_donor_time_series,
)
from ml.src.models.forecaster import (
    LightGBMForecaster,
    NaiveSeasonalBaseline,
    SarimaxForecaster,
    run_walk_forward_evaluation,
)


def test_synthetic_surplus_generation_structure_and_labels() -> None:
    """Verify synthetic dataset generator produces required columns and explicit labels."""
    df = simulate_donor_time_series(
        donor_id="00000000-0000-0000-0000-000000000001",
        donor_name="Test Bakery",
        donor_type="bakery",
        num_days=60,
        seed=42,
    )

    assert len(df) == 60
    assert "surplus_kg" in df.columns
    assert "is_synthetic" in df.columns
    assert "data_provenance" in df.columns
    assert df["is_synthetic"].all(), (
        "Every single row must be explicitly labeled synthetic"
    )
    assert (df["surplus_kg"] >= 0.0).all(), (
        "Surplus weight must always be strictly non-negative"
    )

    # Verify weather and calendar covariates exist
    assert "temperature_c" in df.columns
    assert "precipitation_mm" in df.columns
    assert "day_of_week" in df.columns
    assert "is_weekend" in df.columns


def test_synthetic_seasonality_patterns() -> None:
    """Verify weekend multiplier increases average surplus over weekdays."""
    df = simulate_donor_time_series(
        donor_id="00000000-0000-0000-0000-000000000002",
        donor_name="Test Supermarket",
        donor_type="supermarket",
        num_days=180,
        seed=123,
    )

    weekday_mean = df[~df["is_weekend"]]["surplus_kg"].mean()
    weekend_mean = df[df["is_weekend"]]["surplus_kg"].mean()

    assert weekend_mean > weekday_mean, (
        f"Weekend average ({weekend_mean:.2f}) must exceed weekday average ({weekday_mean:.2f})"
    )


def test_multi_donor_dataset_generation() -> None:
    """Verify multi-donor combined dataset contains multiple archetypes."""
    df_multi = generate_multi_donor_dataset(num_days=30, seed=99)
    assert df_multi["donor_id"].nunique() == 5
    assert set(df_multi["donor_type"].unique()) == set(DEFAULT_PROFILES.keys())
    assert df_multi["is_synthetic"].all()


def test_naive_seasonal_baseline() -> None:
    """Verify Naive 7-day persistence baseline repeats the last 7 values."""
    history = [10.0, 12.0, 11.0, 13.0, 20.0, 25.0, 15.0]  # Mon to Sun
    model = NaiveSeasonalBaseline(season_length=7).fit(history)
    preds = model.predict(steps=14)

    assert len(preds) == 14
    assert list(preds[:7]) == history
    assert list(preds[7:14]) == history


def test_sarimax_forecaster_fit_and_predict() -> None:
    """Verify SARIMAX fits on time series and returns mean, lower, upper bounds."""
    df = simulate_donor_time_series(
        donor_id="test-sarimax",
        donor_name="Sarimax Cafe",
        donor_type="cafe",
        num_days=90,
        seed=42,
    )
    exog_cols = [
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "temperature_c",
        "precipitation_mm",
    ]

    model = SarimaxForecaster(order=(1, 0, 0), seasonal_order=(1, 0, 0, 7))
    model.fit(df["surplus_kg"], exog=df[exog_cols])

    future_exog = df[exog_cols].iloc[:7].copy()
    mean_preds, lower_ci, upper_ci = model.predict(steps=7, exog_future=future_exog)

    assert len(mean_preds) == 7
    assert (mean_preds >= 0.0).all()
    assert (lower_ci <= mean_preds).all()
    assert (upper_ci >= mean_preds).all()


def test_lightgbm_forecaster_fit_and_predict() -> None:
    """Verify LightGBM fits and performs recursive multi-step forecasting."""
    df = simulate_donor_time_series(
        donor_id="test-lgbm",
        donor_name="LGBM Restaurant",
        donor_type="restaurant",
        num_days=90,
        seed=42,
    )
    model = LightGBMForecaster(n_estimators=25, learning_rate=0.1)
    model.fit(df, target_col="surplus_kg")

    future_df = df.iloc[-7:].copy()
    preds = model.predict_recursive(
        history_df=df.iloc[:-7],
        future_exog_df=future_df,
        target_col="surplus_kg",
        steps=7,
    )

    assert len(preds) == 7
    assert (preds >= 0.0).all()


def test_walk_forward_evaluation_beats_naive_baseline() -> None:
    """Verify walk-forward validation confirms SARIMAX / LightGBM beat naive persistence."""
    df = simulate_donor_time_series(
        donor_id="00000000-0000-0000-0000-000000000001",
        donor_name="Daily Harvest Bakery",
        donor_type="bakery",
        num_days=150,
        seed=42,
    )

    results = run_walk_forward_evaluation(
        df=df,
        initial_train_days=90,
        step_days=7,
        horizon_days=7,
        target_col="surplus_kg",
    )

    assert "naive_seasonal_baseline" in results
    assert "sarimax_v1" in results
    assert "lightgbm_v1" in results

    naive_mae = results["naive_seasonal_baseline"].mae
    sarimax_mae = results["sarimax_v1"].mae
    lgbm_mae = results["lightgbm_v1"].mae

    # Both or either must beat naive baseline on MAE
    assert sarimax_mae < naive_mae or lgbm_mae < naive_mae, (
        f"Forecasters failed to beat naive baseline MAE ({naive_mae:.3f}). "
        f"SARIMAX: {sarimax_mae:.3f}, LightGBM: {lgbm_mae:.3f}"
    )
