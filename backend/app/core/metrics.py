"""BountyLoop — Observability & Prometheus Metrics Collector (Phase 12).

Exports real-time operational metrics in standard Prometheus exposition format:
- Request counts by method, path, and HTTP status code
- Request duration histograms/summaries
- Active review queue depth
- Total rescued food weight (kg)
- CV Circuit Breaker state (0=closed, 1=half_open, 2=open)
"""

from __future__ import annotations

import threading
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Donation, DonationStatus, ImpactLog, ReviewQueue, ReviewStatus
from app.services.security import cv_circuit_breaker


class MetricsRegistry:
    """Thread-safe Prometheus metrics collector and exporter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (method, endpoint, status_code) -> count
        self._request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        # endpoint -> list of latency samples (seconds)
        self._latencies: dict[str, list[float]] = defaultdict(list)

    def record_request(
        self, method: str, endpoint: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record an incoming HTTP transaction."""
        with self._lock:
            # Normalize path (collapse UUIDs/IDs to :id)
            normalized_endpoint = self._normalize_path(endpoint)
            self._request_counts[(method, normalized_endpoint, status_code)] += 1
            samples = self._latencies[normalized_endpoint]
            samples.append(duration_seconds)
            # Retain last 200 samples per endpoint to bound memory
            if len(samples) > 200:
                self._latencies[normalized_endpoint] = samples[-200:]

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Strip trailing slash and normalize common query paths."""
        parts = [p for p in path.split("/") if p]
        norm = []
        for p in parts:
            if len(p) >= 32 and ("-" in p or p.isalnum()):  # UUID or hash
                norm.append(":id")
            else:
                norm.append(p)
        return "/" + "/".join(norm) if norm else "/"

    async def generate_prometheus_output(self, db: AsyncSession | None = None) -> str:
        """Generate standard Prometheus exposition format text."""
        lines: list[str] = [
            "# HELP bountyloop_http_requests_total Total number of HTTP requests processed.",
            "# TYPE bountyloop_http_requests_total counter",
        ]

        with self._lock:
            for (method, endpoint, status_code), count in sorted(self._request_counts.items()):
                lines.append(
                    f'bountyloop_http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status_code}"}} {count}'
                )

            lines.append("")
            lines.append(
                "# HELP bountyloop_http_request_duration_seconds HTTP request latency in seconds."
            )
            lines.append("# TYPE bountyloop_http_request_duration_seconds summary")
            for endpoint, samples in sorted(self._latencies.items()):
                if samples:
                    sorted_samples = sorted(samples)
                    n = len(sorted_samples)
                    p50 = sorted_samples[int(n * 0.50)]
                    p95 = sorted_samples[min(int(n * 0.95), n - 1)]
                    lines.append(
                        f'bountyloop_http_request_duration_seconds{{endpoint="{endpoint}",quantile="0.5"}} {p50:.4f}'
                    )
                    lines.append(
                        f'bountyloop_http_request_duration_seconds{{endpoint="{endpoint}",quantile="0.95"}} {p95:.4f}'
                    )

        # Dynamic gauges from database if session is available
        queue_depth = 0
        active_offers = 0
        total_rescued_kg = 0.0

        if db is not None:
            try:
                # 1. Review queue depth (pending items)
                q_depth = select(func.count(ReviewQueue.id)).where(
                    ReviewQueue.status == ReviewStatus.pending
                )
                queue_depth = (await db.execute(q_depth)).scalar_one_or_none() or 0

                # 2. Active open donations
                q_offers = select(func.count(Donation.id)).where(
                    Donation.status == DonationStatus.open
                )
                active_offers = (await db.execute(q_offers)).scalar_one_or_none() or 0

                # 3. Total impact kg rescued
                q_impact = select(func.coalesce(func.sum(ImpactLog.kg_rescued), 0.0))
                total_rescued_kg = float((await db.execute(q_impact)).scalar_one_or_none() or 0.0)
            except Exception:
                pass

        cb_state_val = (
            0
            if cv_circuit_breaker.state == "CLOSED"
            else (1 if cv_circuit_breaker.state == "HALF_OPEN" else 2)
        )

        lines.extend(
            [
                "",
                "# HELP bountyloop_review_queue_depth Current pending donations in human review triage.",
                "# TYPE bountyloop_review_queue_depth gauge",
                f"bountyloop_review_queue_depth {queue_depth}",
                "",
                "# HELP bountyloop_active_offers_count Total surplus donations currently open for recipient claiming.",
                "# TYPE bountyloop_active_offers_count gauge",
                f"bountyloop_active_offers_count {active_offers}",
                "",
                "# HELP bountyloop_impact_kg_rescued_total Total verified weight of surplus food rescued in kilograms.",
                "# TYPE bountyloop_impact_kg_rescued_total counter",
                f"bountyloop_impact_kg_rescued_total {total_rescued_kg:.2f}",
                "",
                "# HELP bountyloop_cv_circuit_breaker_state State of CV inference circuit breaker (0=closed, 1=half_open, 2=open).",
                "# TYPE bountyloop_cv_circuit_breaker_state gauge",
                f"bountyloop_cv_circuit_breaker_state {cb_state_val}",
                "",
            ]
        )

        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
