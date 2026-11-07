# BountyLoop Surplus Forecasting Models & Methodology (Phase 11)

> [!WARNING]
> **CRITICAL SCIENTIFIC & ETHICAL DISCLOSURE**
> All time-series forecasting benchmarks, models, and predictions documented herein are generated using **synthetic per-donor simulation data**. These modeled estimates provide operational routing guidance and volunteer scheduling hints only. They must **never** be presented as empirical food rescue records or guaranteed inventory.
>
> In accordance with the BountyLoop Master Plan (§6 Phase 11), model weights will only be retrained on real donation timestamps once $\ge 8$ weeks (56 days) of real pilot data have been collected with donor consent.

---

## 1. Objective & Operational Role

The surplus forecasting system predicts **when** a participating food donor will generate surplus food before food reaches end-of-day spoilage. This allows:
1. **Proactive Volunteer Routing:** Dispatch coordinators and the autonomous agent can position volunteer drivers near high-probability rescue zones.
2. **Capacity Headroom Management:** Food banks and community pantries can anticipate incoming bulk donations and allocate cold-storage shelf space.
3. **Gentle Evening Donor Prompts:** Donors receive a frictionless reminder the evening before a predicted surplus event ("Tomorrow looks like a surplus day — want to schedule a pickup?"), strictly gated behind the `FORECAST_PROMPTS_ENABLED` feature flag.

```mermaid
flowchart TD
    subgraph Data Layer
        Syn[Synthetic Multi-Donor Time Series] --> Clean[Feature Engineering]
        Real[Empirical Pilot Timestamps (>= 8 Weeks)] -.-> Clean
    end

    subgraph Model Layer
        Clean --> Naive[Naive 7-Day Baseline]
        Clean --> SARIMAX[SARIMAX (1,0,1)x(1,0,0)7 + Exog]
        Clean --> LGBM[LightGBM GBDT (Lags + Rolling)]
    end

    subgraph Evaluation
        Naive --> WF[Walk-Forward Cross-Validation]
        SARIMAX --> WF
        LGBM --> WF
        WF --> Bench[Benchmark Comparison (MAE, RMSE, MAPE)]
    end

    subgraph Serving & Storage
        Bench --> DB[(donor_surplus_forecasts)]
        DB --> API[FastAPI /v1/forecast Endpoints]
        API --> Agent[Agent optimize_pickup Tool Hint]
        API --> Push[Evening Donor Reminder (FORECAST_PROMPTS_ENABLED)]
    end
```

---

## 2. Synthetic Data Generation Architecture (`ml/src/data/synthetic_surplus.py`)

Until a community pilot yields at least 8 continuous weeks of real donation logs, all models are developed and validated against a realistic synthetic time-series engine.

### Mathematical Formulation
For each donor $i$ on calendar day $t$:

$$\text{Surplus}_{i,t} = \max\left(0, \text{Base}_i \cdot M_{\text{dow}}(t) \cdot M_{\text{holiday}}(t) \cdot M_{\text{weather}}(t) \cdot \exp(\epsilon_t)\right)$$

Where:
- $\text{Base}_i$: Baseline surplus capacity in kilograms (e.g. 45 kg for supermarkets, 18 kg for bakeries).
- $M_{\text{dow}}(t)$: Day-of-week multiplier:
  - Weekend factor ($1.25 - 1.70$)
  - Friday surge factor ($1.15 - 1.50$)
- $M_{\text{holiday}}(t)$: Shocks on public holidays and pre-holiday eves ($1.25 - 1.80$).
- $M_{\text{weather}}(t)$: Weather covariate effect ($1.0 + \text{sensitivity} \cdot \min(\text{rain} / 20, 1.5)$).
- $\epsilon_t \sim \mathcal{N}(0, \sigma_i^2)$: Multiplicative log-normal noise ensuring non-negative weights and realistic skewness.

### Donor Archetypes
| Archetype | Base Weight (kg) | Weekend Factor | Friday Factor | Holiday Spike | Weather Sensitivity |
|---|---|---|---|---|---|
| **Supermarket** | 45.0 | 1.45 | 1.30 | 1.60 | 0.15 |
| **Bakery** | 18.0 | 1.35 | 1.20 | 1.40 | 0.08 |
| **Restaurant** | 22.0 | 1.55 | 1.40 | 1.50 | 0.20 |
| **Cafe** | 8.5 | 1.25 | 1.15 | 1.25 | 0.10 |
| **Caterer** | 35.0 | 1.70 | 1.50 | 1.80 | 0.25 |

---

## 3. Evaluated Model Architectures (`ml/src/models/forecaster.py`)

### 1. Naive Seasonal Baseline (7-Day Persistence)
- **Concept:** Predicts day $t$ surplus as the value observed exactly 7 days prior:
  $$\hat{y}_t = y_{t-7}$$
- **Role:** Serves as the benchmark to beat. Any machine learning model that fails to outperform 7-day persistence is rejected for production routing.

### 2. SARIMAX Statistical Model
- **Concept:** Seasonal Autoregressive Integrated Moving Average with Exogenous Regressors:
  $$\text{ARIMA}(p=1, d=0, q=1) \times (P=1, D=0, Q=0)_7$$
- **Exogenous Variables:** `day_of_week`, `is_weekend`, `is_holiday`, `temperature_c`, `precipitation_mm`.
- **Output:** Point forecast with 95% confidence intervals ($\text{lower\_ci}, \text{upper\_ci}$).

### 3. LightGBM Gradient-Boosted Decision Trees
- **Concept:** Recursive autoregressive multi-step regressor with engineered temporal features:
  - **Lags:** $t-1, t-2, t-3, t-7, t-14$
  - **Rolling Statistics:** 7-day and 14-day rolling mean and standard deviation
  - **Calendar Encodings:** Cyclical sine/cosine transformation of day-of-week:
    $$\sin\left(\frac{2\pi \cdot \text{dow}}{7}\right), \quad \cos\left(\frac{2\pi \cdot \text{dow}}{7}\right)$$
  - **Weather Regressors:** Daily temperature (°C) and precipitation (mm).
- **Inference:** Autoregressive recursive multi-step forecasting across the 7-day horizon.

---

## 4. Rolling Walk-Forward Validation Protocol

> [!IMPORTANT]
> **No Future Data Leakage:** Random train/test splits are strictly prohibited for time-series evaluation. Shuffling time-series leaks future autocorrelation into past folds.

- **Protocol:**
  1. Initial training window: $T_0 = 90$ days.
  2. Forecast horizon: $H = 7$ days.
  3. Step size: Advance cutoff by 7 days per fold.
  4. Repeat until series end (180 days total; 84 evaluation points across 12 rolling folds).

### Benchmark Comparison Results

| Model | MAE (kg) | RMSE (kg) | MAPE (%) | Evaluation Points | Status |
|---|---|---|---|---|---|
| **Naive Seasonal Baseline ($y_{t-7}$)** | 3.209 | 4.122 | 15.96% | 84 | Reference Baseline |
| **LightGBM v1 (GBDT)** | 2.690 | 3.193 | 14.07% | 84 | **Beats Baseline ✅ (-16.2% MAE)** |
| **SARIMAX v1 (Order $(1,0,1)\times(1,0,0)_7$)** | 0.487 | 0.624 | 2.50% | 84 | **Beats Baseline ✅ (-84.8% MAE)** |

Both SARIMAX and LightGBM beat the naive 7-day seasonal persistence baseline on MAE, RMSE, and MAPE.

---

## 5. Database Schema & Persistence

### Table: `donor_surplus_forecasts`
Implemented via Alembic migration `004_donor_surplus_forecasts.py`:

```sql
CREATE TABLE donor_surplus_forecasts (
    id UUID PRIMARY KEY,
    donor_id UUID NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    predicted_kg FLOAT NOT NULL,
    confidence_lower_kg FLOAT,
    confidence_upper_kg FLOAT,
    model_version VARCHAR(50) NOT NULL DEFAULT 'sarimax_v1',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_donor_forecast_date_model UNIQUE (donor_id, forecast_date, model_version)
);

CREATE INDEX ix_donor_surplus_forecasts_donor_id ON donor_surplus_forecasts(donor_id);
CREATE INDEX ix_donor_surplus_forecasts_forecast_date ON donor_surplus_forecasts(forecast_date);
CREATE INDEX ix_donor_surplus_forecasts_model_version ON donor_surplus_forecasts(model_version);
```

### Idempotency & Conflict Resolution
The unique constraint on `(donor_id, forecast_date, model_version)` guarantees that nightly batch updates or re-runs atomically replace previous forecasts without duplicate record accumulation.

---

## 6. API Endpoints (`backend/app/api/v1/routes/forecast.py`)

| Method | Path | Summary | Description |
|---|---|---|---|
| `GET` | `/v1/forecast/donor/{id}` | Donor Forecast | 7-day ahead surplus forecast with confidence bounds and synthetic flag |
| `GET` | `/v1/forecast/aggregate` | Community Aggregate | Sum of predicted surplus weights across all donors for logistics planning |
| `POST` | `/v1/forecast/generate` | Batch Generator | Computes and persists fresh forecasts for specified or all active donors |
| `GET` | `/v1/forecast/metrics` | Validation Metrics | Walk-forward cross-validation performance comparison table |
| `POST` | `/v1/forecast/prompts/trigger` | Trigger Reminders | Evaluates next-day surplus and queues donor reminders (gated by feature flag) |

---

## 7. Feature Flag Specification (`FORECAST_PROMPTS_ENABLED`)

Donor reminder prompts ("Tomorrow looks like a surplus day — want to schedule a pickup?") are strictly isolated behind the `FORECAST_PROMPTS_ENABLED` configuration:
- **Default:** `False`
- **When Disabled:** `POST /v1/forecast/prompts/trigger` safely returns:
  ```json
  {
    "prompts_enabled": false,
    "prompts_dispatched": 0,
    "details": [],
    "message": "Forecast prompts are disabled via FORECAST_PROMPTS_ENABLED feature flag."
  }
  ```
- **Zero Side Effects:** Toggling `FORECAST_PROMPTS_ENABLED` off has zero impact on active donations, claim matching, routing, or database integrity.

---

## 8. Transition Criteria to Real Pilot Data (Phase 14)

1. **Volume Threshold:** Minimum 8 weeks ($\ge 56$ days) of continuous empirical donation timestamps from pilot donors.
2. **Provenance Separation:** Once empirical data exists, records trained on real data set `is_synthetic = False`.
3. **Delta Reporting:** A retrospective delta analysis comparing synthetic model error vs real pilot model error will be appended to this document.

