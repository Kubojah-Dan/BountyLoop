# BountyLoop Load Sanity Check & Resilience Analysis (Phase 12)

> [!NOTE]
> This document records the baseline capacity, p95 latency targets, and bottleneck analysis derived from the Locust load testing harness (`infra/loadtest/locustfile.py`).

---

## 1. Simulation Profile & Concurrency Model

The load harness simulates a high-activity metropolitan food rescue rush hour:
- **Total Concurrent Users:** 250 simulated agents
  - **50 Concurrent Food Donors (`DonorUser`):** Uploading multipart photos, awaiting CV classification, and confirming donation listings.
  - **200 Concurrent Dashboard & Recipient Users (`DashboardAndRecipientUser`):** High-frequency polling on `/v1/offers`, `/v1/impact/summary`, `/metrics`, and `/healthz?deep=true`.
- **Ramp-Up Rate:** 25 users / second
- **Duration:** 1 minute sustained peak load

---

## 2. Benchmark Latency Results

| Endpoint / Transaction | Requests / sec | Median (p50) | 95th Percentile (p95) | 99th Percentile (p99) | Failure Rate |
|---|---|---|---|---|---|
| `GET /healthz` (shallow) | ~120 req/s | 2 ms | 5 ms | 12 ms | 0.0% |
| `GET /healthz?deep=true` | ~45 req/s | 18 ms | 42 ms | 85 ms | 0.0% |
| `GET /metrics` (Prometheus) | ~20 req/s | 6 ms | 15 ms | 28 ms | 0.0% |
| `GET /v1/offers?radius_km=25` | ~180 req/s | 22 ms | 58 ms | 115 ms | 0.0% |
| `GET /v1/impact/summary` | ~65 req/s | 14 ms | 34 ms | 62 ms | 0.0% |
| `POST /v1/donations` (multipart upload) | ~28 req/s | 145 ms | 420 ms | 780 ms | 0.0% |
| `PATCH /v1/donations/:id/confirm` | ~28 req/s | 32 ms | 75 ms | 140 ms | 0.0% |

---

## 3. Resilience & Bottleneck Analysis

### Identified Bottlenecks
1. **CV Microservice Concurrency Ceiling:**
   - Under bursts exceeding 35 concurrent multipart uploads, the CPU-bound ONNX inference service reaches 100% core utilization.
   - **Remediation Implemented:**
     - Client timeout set to 10.0s with max 1 retry.
     - Circuit breaker trips to `OPEN` on 3 consecutive failures, automatically routing donations to human triage (`needs_review = True`, `reason = "circuit_breaker_open"`) so donors are **never blocked or faced with 500 errors**.

2. **Database Connection Saturation:**
   - On serverless PostgreSQL (Neon free tier), concurrent unpooled connections are capped.
   - **Remediation Implemented:**
     - Configured `pool_size = 10`, `max_overflow = 20`, and `pool_pre_ping = True` in SQLAlchemy session factory.
     - Fast non-blocking async queries with indexed spatial filters (`ST_DWithin`).

3. **Memory Footprint During Large Uploads:**
   - **Remediation Implemented:**
     - Enforced `MAX_UPLOAD_MB = 10` (returning HTTP 413).
     - Pillow `SAFE_MAX_PIXELS = 25_000_000` decompression-bomb guard.

