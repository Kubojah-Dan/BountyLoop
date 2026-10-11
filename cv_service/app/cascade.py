"""BountyLoop — Cascade Decision Engine.

Evaluates multi-head CV model outputs against safety gates:
- Auto Create: item_conf >= 0.90 AND freshness_conf >= 0.90 AND hazard == 'none' AND not spoiled
- Ask Donor Confirm: 0.60 <= conf < 0.90 AND hazard == 'none' AND not spoiled
- Human Review Queue: conf < 0.60 OR hazard != 'none' OR spoiled
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CascadeResult:
    """Standardized result of CV cascade safety gate evaluation."""

    item: str
    item_confidence: float
    freshness: str
    freshness_confidence: float
    hazard_flag: str
    hazard_confidence: float
    action: str  # "auto_create" | "ask_donor_confirm" | "human_review_queue"
    needs_review: bool
    review_reason: str | None  # "low_confidence" | "hazard" | None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        return {
            "item": self.item,
            "item_confidence": round(self.item_confidence, 4),
            "freshness": self.freshness,
            "freshness_confidence": round(self.freshness_confidence, 4),
            "hazard_flag": self.hazard_flag,
            "hazard_confidence": round(self.hazard_confidence, 4),
            "action": self.action,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
        }


class CascadeDecisionEngine:
    """Applies confidence gating and safety policies to CV inference outputs."""

    def __init__(
        self,
        auto_conf: float | None = None,
        confirm_conf: float | None = None,
        hazard_forces_review: bool | None = None,
    ) -> None:
        self.auto_conf = (
            auto_conf
            if auto_conf is not None
            else float(os.environ.get("AUTO_CONF", "0.90"))
        )
        self.confirm_conf = (
            confirm_conf
            if confirm_conf is not None
            else float(os.environ.get("CONFIRM_CONF", "0.60"))
        )
        if hazard_forces_review is not None:
            self.hazard_forces_review = hazard_forces_review
        else:
            self.hazard_forces_review = (
                os.environ.get("HAZARD_FORCES_REVIEW", "true").lower() == "true"
            )

    def evaluate(
        self,
        item: str,
        item_confidence: float,
        freshness: str,
        freshness_confidence: float,
        hazard_flag: str,
        hazard_confidence: float,
    ) -> CascadeResult:
        """Evaluate predictions and decide downstream routing action."""
        # Check if item is classified as spoiled
        is_spoiled = freshness in {"spoiled", "grade_0_spoiled"}

        # 1. Chemical/Physical hazard safety gate
        if self.hazard_forces_review and hazard_flag != "none":
            logger.warning(
                "Hazard detected (%s, conf=%.2f) -> human review required",
                hazard_flag,
                hazard_confidence,
            )
            return CascadeResult(
                item=item,
                item_confidence=item_confidence,
                freshness=freshness,
                freshness_confidence=freshness_confidence,
                hazard_flag=hazard_flag,
                hazard_confidence=hazard_confidence,
                action="human_review_queue",
                needs_review=True,
                review_reason="hazard",
            )

        # 2. Food spoiled safety gate
        if is_spoiled:
            logger.warning(
                "Food spoiled (%s, conf=%.2f) -> human review required",
                freshness,
                freshness_confidence,
            )
            return CascadeResult(
                item=item,
                item_confidence=item_confidence,
                freshness=freshness,
                freshness_confidence=freshness_confidence,
                hazard_flag=hazard_flag,
                hazard_confidence=hazard_confidence,
                action="human_review_queue",
                needs_review=True,
                review_reason="hazard",
            )

        # 3. High confidence gate -> AUTO CREATE
        if (
            item_confidence >= self.auto_conf
            and freshness_confidence >= self.auto_conf
        ):
            return CascadeResult(
                item=item,
                item_confidence=item_confidence,
                freshness=freshness,
                freshness_confidence=freshness_confidence,
                hazard_flag=hazard_flag,
                hazard_confidence=hazard_confidence,
                action="auto_create",
                needs_review=False,
                review_reason=None,
            )

        # 4. Moderate confidence gate -> ASK DONOR CONFIRM
        if (
            item_confidence >= self.confirm_conf
            and freshness_confidence >= self.confirm_conf
        ):
            return CascadeResult(
                item=item,
                item_confidence=item_confidence,
                freshness=freshness,
                freshness_confidence=freshness_confidence,
                hazard_flag=hazard_flag,
                hazard_confidence=hazard_confidence,
                action="ask_donor_confirm",
                needs_review=False,
                review_reason=None,
            )

        # 5. Low confidence gate -> HUMAN REVIEW QUEUE
        logger.info(
            "Low confidence (item=%.2f, freshness=%.2f) -> human review required",
            item_confidence,
            freshness_confidence,
        )
        return CascadeResult(
            item=item,
            item_confidence=item_confidence,
            freshness=freshness,
            freshness_confidence=freshness_confidence,
            hazard_flag=hazard_flag,
            hazard_confidence=hazard_confidence,
            action="human_review_queue",
            needs_review=True,
            review_reason="low_confidence",
        )
