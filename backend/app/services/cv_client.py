"""BountyLoop — Computer Vision Microservice Client.

Calls the external CV inference microservice (POST /predict) with:
- Configurable timeouts
- Automatic retry on connection failure
- Safe circuit-breaker fallback when CV service is unreachable or errors out:
  marks donation needs_review=True with item=other_unclassified so donors are never blocked.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.db.models.enums import FoodCategory, FreshnessGrade, HazardFlag

logger = logging.getLogger(__name__)


class CVClient:
    """Async client for BountyLoop CV inference microservice."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.cv_service_url).rstrip("/")
        self.timeout = (
            timeout_seconds if timeout_seconds is not None else settings.cv_timeout_seconds
        )
        self.max_retries = max_retries if max_retries is not None else settings.cv_max_retries

    def get_fallback_prediction(self, reason: str = "cv_offline") -> dict[str, Any]:
        """Return safe fallback classification when CV microservice is unreachable."""
        logger.warning(
            "CV microservice fallback activated (reason: %s). Flagging for human review.",
            reason,
        )
        return {
            "item": FoodCategory.other_unclassified,
            "item_confidence": 0.0,
            "freshness": FreshnessGrade.grade_1_poor,
            "freshness_confidence": 0.0,
            "hazard_flag": HazardFlag.none,
            "hazard_confidence": 0.0,
            "action": "human_review_queue",
            "needs_review": True,
            "review_reason": "low_confidence",
            "model_versions": {"cv_status": f"offline_fallback_{reason}"},
            "latency_ms": 0.0,
        }

    async def predict(
        self,
        image_bytes: bytes,
        filename: str = "food.jpg",
        content_type: str = "image/jpeg",
        apply_tta: bool | None = None,
    ) -> dict[str, Any]:
        """Send image to CV microservice /predict and return parsed result.

        If CV service is unavailable or errors after retries, returns safe fallback.
        """
        predict_url = f"{self.base_url}/predict"
        params = {}
        if apply_tta is not None:
            params["tta"] = "true" if apply_tta else "false"

        files = {"file": (filename, image_bytes, content_type)}

        # Try with retry logic
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(predict_url, files=files, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    # Map to canonical enums
                    item_str = data.get("item", FoodCategory.other_unclassified.value)
                    try:
                        item_enum = FoodCategory(item_str)
                    except ValueError:
                        item_enum = FoodCategory.other_unclassified

                    freshness_str = data.get("freshness", FreshnessGrade.grade_1_poor.value)
                    try:
                        freshness_enum = FreshnessGrade(freshness_str)
                    except ValueError:
                        freshness_enum = FreshnessGrade.grade_1_poor

                    hazard_str = data.get("hazard_flag", HazardFlag.none.value)
                    try:
                        hazard_enum = HazardFlag(hazard_str)
                    except ValueError:
                        hazard_enum = HazardFlag.none

                    return {
                        "item": item_enum,
                        "item_confidence": float(data.get("item_confidence", 0.0)),
                        "freshness": freshness_enum,
                        "freshness_confidence": float(data.get("freshness_confidence", 0.0)),
                        "hazard_flag": hazard_enum,
                        "hazard_confidence": float(data.get("hazard_confidence", 0.0)),
                        "action": data.get("action", "ask_donor_confirm"),
                        "needs_review": bool(data.get("needs_review", False)),
                        "review_reason": data.get("review_reason"),
                        "model_versions": data.get("model_versions", {}),
                        "latency_ms": float(data.get("latency_ms", 0.0)),
                    }

                logger.warning(
                    "CV service returned status %d (attempt %d/%d): %s",
                    resp.status_code,
                    attempt + 1,
                    self.max_retries + 1,
                    resp.text,
                )
                if resp.status_code < 500:
                    # Client errors (400, 413, etc.) shouldn't be retried
                    return self.get_fallback_prediction(reason=f"http_{resp.status_code}")

            except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    "CV microservice request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )

        return self.get_fallback_prediction(
            reason=f"connection_error_{type(last_error).__name__}" if last_error else "unknown"
        )


cv_client = CVClient()
