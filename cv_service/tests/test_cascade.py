"""BountyLoop — Tests for Cascade Decision Engine.

Validates safety policies and confidence gates:
- Auto Create: item_conf >= 0.90 AND freshness_conf >= 0.90 AND hazard == 'none' AND not spoiled
- Ask Donor Confirm: 0.60 <= conf < 0.90 AND hazard == 'none' AND not spoiled
- Human Review Queue: conf < 0.60 OR hazard != 'none' OR spoiled
"""

from __future__ import annotations

import pytest

from app.cascade import CascadeDecisionEngine


@pytest.fixture
def engine() -> CascadeDecisionEngine:
    return CascadeDecisionEngine(
        auto_conf=0.90,
        confirm_conf=0.60,
        hazard_forces_review=True,
    )


def test_cascade_auto_create(engine: CascadeDecisionEngine) -> None:
    """High confidence, no hazard, fresh food -> auto create."""
    res = engine.evaluate(
        item="produce_fruit",
        item_confidence=0.95,
        freshness="grade_3_fresh",
        freshness_confidence=0.92,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res.action == "auto_create"
    assert res.needs_review is False
    assert res.review_reason is None
    assert res.item == "produce_fruit"


def test_cascade_ask_donor_confirm_item(engine: CascadeDecisionEngine) -> None:
    """Moderate item confidence (0.60 <= conf < 0.90) -> ask donor confirm."""
    res = engine.evaluate(
        item="bread_bakery",
        item_confidence=0.74,
        freshness="grade_3_fresh",
        freshness_confidence=0.95,
        hazard_flag="none",
        hazard_confidence=0.98,
    )
    assert res.action == "ask_donor_confirm"
    assert res.needs_review is False
    assert res.review_reason is None


def test_cascade_ask_donor_confirm_freshness(engine: CascadeDecisionEngine) -> None:
    """Moderate freshness confidence (0.60 <= conf < 0.90) -> ask donor confirm."""
    res = engine.evaluate(
        item="dairy",
        item_confidence=0.92,
        freshness="grade_2_good",
        freshness_confidence=0.65,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res.action == "ask_donor_confirm"
    assert res.needs_review is False
    assert res.review_reason is None


def test_cascade_low_confidence_item_triggers_review(
    engine: CascadeDecisionEngine,
) -> None:
    """Low item confidence (<0.60) -> human review queue with low_confidence."""
    res = engine.evaluate(
        item="produce_vegetable",
        item_confidence=0.54,
        freshness="grade_3_fresh",
        freshness_confidence=0.95,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res.action == "human_review_queue"
    assert res.needs_review is True
    assert res.review_reason == "low_confidence"


def test_cascade_low_confidence_freshness_triggers_review(
    engine: CascadeDecisionEngine,
) -> None:
    """Low freshness confidence (<0.60) -> human review queue with low_confidence."""
    res = engine.evaluate(
        item="prepared_cooked",
        item_confidence=0.95,
        freshness="grade_2_good",
        freshness_confidence=0.48,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res.action == "human_review_queue"
    assert res.needs_review is True
    assert res.review_reason == "low_confidence"


def test_cascade_hazard_flag_forces_review(engine: CascadeDecisionEngine) -> None:
    """Suspected contamination/formalin forces human review regardless of confidences."""
    res = engine.evaluate(
        item="produce_fruit",
        item_confidence=0.99,
        freshness="grade_3_fresh",
        freshness_confidence=0.99,
        hazard_flag="suspected_contamination_or_formalin",
        hazard_confidence=0.85,
    )
    assert res.action == "human_review_queue"
    assert res.needs_review is True
    assert res.review_reason == "hazard"


def test_cascade_spoiled_food_forces_review(engine: CascadeDecisionEngine) -> None:
    """Spoiled grade forces human review as safety violation."""
    # Test grade_0_spoiled
    res_v2 = engine.evaluate(
        item="produce_fruit",
        item_confidence=0.96,
        freshness="grade_0_spoiled",
        freshness_confidence=0.95,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res_v2.action == "human_review_queue"
    assert res_v2.needs_review is True
    assert res_v2.review_reason == "hazard"

    # Test v1 spoiled
    res_v1 = engine.evaluate(
        item="produce_fruit",
        item_confidence=0.96,
        freshness="spoiled",
        freshness_confidence=0.95,
        hazard_flag="none",
        hazard_confidence=0.99,
    )
    assert res_v1.action == "human_review_queue"
    assert res_v1.needs_review is True
    assert res_v1.review_reason == "hazard"


def test_cascade_boundary_values(engine: CascadeDecisionEngine) -> None:
    """Test exact boundary values at 0.90 and 0.60 thresholds."""
    # Exactly 0.90 / 0.90 -> auto_create
    res_exact_auto = engine.evaluate(
        item="meat_fish",
        item_confidence=0.90,
        freshness="grade_3_fresh",
        freshness_confidence=0.90,
        hazard_flag="none",
        hazard_confidence=0.95,
    )
    assert res_exact_auto.action == "auto_create"
    assert res_exact_auto.needs_review is False

    # 0.899 -> ask_donor_confirm
    res_just_below_auto = engine.evaluate(
        item="meat_fish",
        item_confidence=0.899,
        freshness="grade_3_fresh",
        freshness_confidence=0.90,
        hazard_flag="none",
        hazard_confidence=0.95,
    )
    assert res_just_below_auto.action == "ask_donor_confirm"
    assert res_just_below_auto.needs_review is False

    # Exactly 0.60 / 0.60 -> ask_donor_confirm
    res_exact_confirm = engine.evaluate(
        item="meat_fish",
        item_confidence=0.60,
        freshness="grade_2_good",
        freshness_confidence=0.60,
        hazard_flag="none",
        hazard_confidence=0.95,
    )
    assert res_exact_confirm.action == "ask_donor_confirm"
    assert res_exact_confirm.needs_review is False

    # 0.599 -> human_review_queue
    res_below_confirm = engine.evaluate(
        item="meat_fish",
        item_confidence=0.599,
        freshness="grade_2_good",
        freshness_confidence=0.60,
        hazard_flag="none",
        hazard_confidence=0.95,
    )
    assert res_below_confirm.action == "human_review_queue"
    assert res_below_confirm.needs_review is True
    assert res_below_confirm.review_reason == "low_confidence"
