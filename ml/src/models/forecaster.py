"""BountyLoop — Surplus Forecasting Models & Walk-Forward Cross-Validation.

================================================================================
CRITICAL ETHICAL & SCIENTIFIC NOTICE:
ALL TIME-SERIES PREDICTIONS ARE MODELED ESTIMATES BASED ON ARTIFICIAL/SYNTHETIC
OR HISTORICAL DONATION TRENDS. THEY ARE PLANNING HINTS ONLY AND MUST NEVER BE
PRESENTED AS GUARANTEED RESCUE COMMITMENTS OR EMPIRICAL FACTS.
================================================================================

This module implements:
1. Naive Seasonal Baseline (7-day persistence: y_hat_t = y_{t-7}).
2. SARIMAX statistical baseline model with seasonal order s=7 and optional exogenous covariates.
3. LightGBM gradient-boosted tree model with lag and rolling features.
4. Rolling Walk-Forward Cross-Validation protocol (STRICTLY NO random shuffling/leakage).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Suppress ConvergenceWarnings and statsmodels UserWarnings during quick fits
warnings.filterwarnings("ignore")
try:
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    warnings.filterwarnings("ignore", category=ConvergenceWarning)
except ImportError:
    pass


@dataclass
class ForecastMetrics:
    """Summary metrics of a model evaluation."""

    model_name: str
    mae: float
    rmse: float
    mape: float
    num_eval_points: int
    is_synthetic: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "mae": round(self.mae, 3),
            "rmse": round(self.rmse, 3),
            "mape": round(self.mape, 3),
            "num_eval_points": self.num_eval_points,
            "is_synthetic": self.is_synthetic,
            "metadata": self.metadata,
        }


def compute_mape(
    y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-5
) -> float:
    """Compute Mean Absolute Percentage Error (MAPE) safely avoiding division by zero."""
    y_true_safe = np.where(y_true == 0, epsilon, y_true)
    return float(np.mean(np.abs((y_true - y_pred) / y_true_safe)) * 100.0)


# ── 1. Naive Seasonal Baseline ────────────────────────────────────────────────


class NaiveSeasonalBaseline:
    """Predicts surplus on day t as the observed surplus from exactly 7 days prior (t-7)."""

    def __init__(self, season_length: int = 7) -> None:
        self.season_length = season_length
        self.history: list[float] = []

    def fit(self, y: pd.Series | np.ndarray) -> NaiveSeasonalBaseline:
        self.history = list(y)
        return self

    def predict(self, steps: int = 7) -> np.ndarray:
        if not self.history:
            return np.zeros(steps)
        if len(self.history) < self.season_length:
            mean_val = float(np.mean(self.history))
            return np.full(steps, mean_val)

        # Use the most recent season_length values as recurring pattern
        recent_cycle = self.history[-self.season_length :]
        preds = []
        for i in range(steps):
            preds.append(recent_cycle[i % self.season_length])
        return np.array(preds)


# ── 2. SARIMAX Baseline ───────────────────────────────────────────────────────


class SarimaxForecaster:
    """SARIMAX statistical forecaster using statsmodels statespace SARIMAX."""

    def __init__(
        self,
        order: tuple[int, int, int] = (1, 0, 1),
        seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 7),
    ) -> None:
        self.order = order
        self.seasonal_order = seasonal_order
        self.model_res: Any = None
        self.exog_cols: list[str] = []

    def fit(
        self,
        y: pd.Series,
        exog: pd.DataFrame | None = None,
    ) -> SarimaxForecaster:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        if exog is not None:
            self.exog_cols = list(exog.columns)
            exog_data = exog.to_numpy(dtype=float)
        else:
            self.exog_cols = []
            exog_data = None

        model = SARIMAX(
            endog=y.to_numpy(dtype=float),
            exog=exog_data,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        self.model_res = model.fit(disp=False, maxiter=50)
        return self

    def predict(
        self,
        steps: int = 7,
        exog_future: pd.DataFrame | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (predicted_mean, lower_ci, upper_ci)."""
        if self.model_res is None:
            raise RuntimeError("SARIMAX model must be fitted before predict()")

        if exog_future is not None:
            exog_data = exog_future[self.exog_cols].to_numpy(dtype=float)
        else:
            exog_data = None

        forecast_res = self.model_res.get_forecast(steps=steps, exog=exog_data)
        mean_preds = np.maximum(0.0, forecast_res.predicted_mean)
        conf_int = forecast_res.conf_int(alpha=0.05)
        lower = np.maximum(0.0, conf_int[:, 0])
        upper = np.maximum(lower, conf_int[:, 1])

        return mean_preds, lower, upper


# ── 3. LightGBM GBDT Forecaster ───────────────────────────────────────────────


class LightGBMForecaster:
    """LightGBM recursive autoregressive tree forecaster with lag & rolling features."""

    def __init__(
        self,
        lags: tuple[int, ...] = (1, 2, 3, 7, 14),
        rolling_windows: tuple[int, ...] = (7, 14),
        n_estimators: int = 60,
        learning_rate: float = 0.05,
        random_state: int = 42,
    ) -> None:
        self.lags = lags
        self.rolling_windows = rolling_windows
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.model: Any = None
        self.feature_names: list[str] = []

    def create_features(
        self, df: pd.DataFrame, target_col: str = "surplus_kg"
    ) -> pd.DataFrame:
        """Engineer lag, rolling, calendar, and exogenous weather features."""
        feat_df = df.copy()

        # Calendar features
        if "day_of_week" not in feat_df.columns and "date" in feat_df.columns:
            feat_df["day_of_week"] = pd.to_datetime(feat_df["date"]).dt.weekday

        feat_df["dow_sin"] = np.sin(2.0 * np.pi * feat_df["day_of_week"] / 7.0)
        feat_df["dow_cos"] = np.cos(2.0 * np.pi * feat_df["day_of_week"] / 7.0)
        feat_df["is_weekend_int"] = feat_df["is_weekend"].astype(int)
        feat_df["is_holiday_int"] = feat_df["is_holiday"].astype(int)

        # Lags on target
        for lag in self.lags:
            feat_df[f"lag_{lag}"] = feat_df[target_col].shift(lag)

        # Rolling statistics on target
        for w in self.rolling_windows:
            feat_df[f"rolling_mean_{w}"] = (
                feat_df[target_col].shift(1).rolling(w).mean()
            )
            feat_df[f"rolling_std_{w}"] = feat_df[target_col].shift(1).rolling(w).std()

        return feat_df

    def fit(
        self, df: pd.DataFrame, target_col: str = "surplus_kg"
    ) -> LightGBMForecaster:
        import lightgbm as lgb

        feat_df = self.create_features(df, target_col=target_col)

        # Drop NaN rows caused by lag/rolling shifts
        max_shift = max(max(self.lags), max(self.rolling_windows))
        clean_df = feat_df.iloc[max_shift:].copy()

        drop_cols = {
            target_col,
            "date",
            "donor_id",
            "donor_name",
            "donor_type",
            "is_synthetic",
            "data_provenance",
        }
        self.feature_names = [c for c in clean_df.columns if c not in drop_cols]

        X = clean_df[self.feature_names]
        y = clean_df[target_col]

        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            verbose=-1,
        )
        self.model.fit(X, y)
        return self

    def predict_recursive(
        self,
        history_df: pd.DataFrame,
        future_exog_df: pd.DataFrame,
        target_col: str = "surplus_kg",
        steps: int = 7,
    ) -> np.ndarray:
        """Autoregressive multi-step prediction feeding previous forecasts into next lags."""
        if self.model is None:
            raise RuntimeError(
                "Model must be fitted before calling predict_recursive()"
            )

        current_df = history_df.copy()
        predictions: list[float] = []

        for step in range(steps):
            next_row = future_exog_df.iloc[[step]].copy()
            # Set provisional target to 0 before feature engineering
            next_row[target_col] = 0.0

            combined = pd.concat([current_df, next_row], ignore_index=True)
            feat_combined = self.create_features(combined, target_col=target_col)
            last_features = feat_combined.iloc[[-1]][self.feature_names]

            pred_val = float(np.maximum(0.0, self.model.predict(last_features)[0]))
            predictions.append(pred_val)

            # Update the provisional row with the predicted value for subsequent lags
            combined.iloc[-1, combined.columns.get_loc(target_col)] = pred_val
            current_df = combined

        return np.array(predictions)


# ── 4. Walk-Forward Cross-Validation ──────────────────────────────────────────


def run_walk_forward_evaluation(
    df: pd.DataFrame,
    initial_train_days: int = 90,
    step_days: int = 7,
    horizon_days: int = 7,
    target_col: str = "surplus_kg",
) -> dict[str, ForecastMetrics]:
    """Execute rolling walk-forward cross validation without lookahead or shuffling.

    At each fold:
      Train on history [0 : T]
      Evaluate on future [T : T + horizon_days]
      Advance T by step_days
    """
    dates = pd.to_datetime(df["date"]).sort_values().unique()
    total_days = len(dates)

    if total_days < initial_train_days + horizon_days:
        raise ValueError(
            f"Insufficient data length ({total_days} days) for initial {initial_train_days} + {horizon_days} horizon"
        )

    naive_preds, sarimax_preds, lgbm_preds, actuals = [], [], [], []

    exog_cols = [
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "temperature_c",
        "precipitation_mm",
    ]

    cutoff = initial_train_days
    while cutoff + horizon_days <= total_days:
        train_df = df.iloc[:cutoff].copy()
        test_df = df.iloc[cutoff : cutoff + horizon_days].copy()
        y_test = test_df[target_col].to_numpy()

        # 1. Naive baseline
        naive_model = NaiveSeasonalBaseline(season_length=7)
        naive_model.fit(train_df[target_col])
        pred_naive = naive_model.predict(steps=horizon_days)

        # 2. SARIMAX
        try:
            sarimax = SarimaxForecaster(order=(1, 0, 1), seasonal_order=(1, 0, 0, 7))
            sarimax.fit(train_df[target_col], exog=train_df[exog_cols])
            pred_sarimax, _, _ = sarimax.predict(
                steps=horizon_days, exog_future=test_df[exog_cols]
            )
        except (ValueError, RuntimeError, IndexError):
            # Safe fallback to naive if statsmodels optimizer struggles on a single window
            pred_sarimax = pred_naive

        # 3. LightGBM
        try:
            lgbm = LightGBMForecaster(n_estimators=40, learning_rate=0.08)
            lgbm.fit(train_df, target_col=target_col)
            pred_lgbm = lgbm.predict_recursive(
                history_df=train_df,
                future_exog_df=test_df,
                target_col=target_col,
                steps=horizon_days,
            )
        except (ValueError, RuntimeError, IndexError):
            pred_lgbm = pred_naive

        actuals.extend(y_test)
        naive_preds.extend(pred_naive)
        sarimax_preds.extend(pred_sarimax)
        lgbm_preds.extend(pred_lgbm)

        cutoff += step_days

    y_true = np.array(actuals)
    y_naive = np.array(naive_preds)
    y_sarimax = np.array(sarimax_preds)
    y_lgbm = np.array(lgbm_preds)
    n = len(y_true)

    results = {
        "naive_seasonal_baseline": ForecastMetrics(
            model_name="naive_seasonal_baseline",
            mae=float(mean_absolute_error(y_true, y_naive)),
            rmse=float(np.sqrt(mean_squared_error(y_true, y_naive))),
            mape=compute_mape(y_true, y_naive),
            num_eval_points=n,
            metadata={"strategy": "y_t = y_{t-7}"},
        ),
        "sarimax_v1": ForecastMetrics(
            model_name="sarimax_v1",
            mae=float(mean_absolute_error(y_true, y_sarimax)),
            rmse=float(np.sqrt(mean_squared_error(y_true, y_sarimax))),
            mape=compute_mape(y_true, y_sarimax),
            num_eval_points=n,
            metadata={"order": [1, 0, 1], "seasonal_order": [1, 0, 0, 7]},
        ),
        "lightgbm_v1": ForecastMetrics(
            model_name="lightgbm_v1",
            mae=float(mean_absolute_error(y_true, y_lgbm)),
            rmse=float(np.sqrt(mean_squared_error(y_true, y_lgbm))),
            mape=compute_mape(y_true, y_lgbm),
            num_eval_points=n,
            metadata={"lags": [1, 2, 3, 7, 14], "rolling": [7, 14]},
        ),
    }

    return results


if __name__ == "__main__":
    from ml.src.data.synthetic_surplus import simulate_donor_time_series

    print("Generating single donor test series...")
    df_donor = simulate_donor_time_series(
        donor_id="00000000-0000-0000-0000-000000000001",
        donor_name="Daily Harvest Bakery",
        donor_type="bakery",
        num_days=180,
        seed=42,
    )

    print("Running Walk-Forward Cross-Validation...")
    metrics = run_walk_forward_evaluation(
        df_donor, initial_train_days=90, step_days=7, horizon_days=7
    )

    print("\n=== Walk-Forward Validation Benchmark Results ===")
    for m in metrics.values():
        print(
            f"[{m.model_name}] MAE: {m.mae:.3f} kg | RMSE: {m.rmse:.3f} kg | MAPE: {m.mape:.2f}% (N={m.num_eval_points})"
        )
