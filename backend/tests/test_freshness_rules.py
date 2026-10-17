"""BountyLoop — Unit Tests for Freshness Rules and Expiry Calculation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models.enums import FoodCategory, FreshnessGrade
from app.services.freshness_rules import calculate_expiry, get_hours_to_spoil


def test_hours_to_spoil_produce_fruit() -> None:
    """Produce fruit shelf-life decreases from grade 3 down to spoiled."""
    assert get_hours_to_spoil(FoodCategory.produce_fruit, FreshnessGrade.grade_3_fresh) == 72
    assert get_hours_to_spoil(FoodCategory.produce_fruit, FreshnessGrade.grade_2_good) == 48
    assert get_hours_to_spoil(FoodCategory.produce_fruit, FreshnessGrade.grade_1_poor) == 24
    assert get_hours_to_spoil(FoodCategory.produce_fruit, FreshnessGrade.grade_0_spoiled) == 0


def test_hours_to_spoil_dairy_and_meat() -> None:
    """Perishable categories (dairy, meat, prepared) have shorter shelf life."""
    assert get_hours_to_spoil(FoodCategory.dairy, FreshnessGrade.grade_2_good) == 24
    assert get_hours_to_spoil(FoodCategory.meat_fish, FreshnessGrade.grade_2_good) == 12
    assert get_hours_to_spoil(FoodCategory.prepared_cooked, FreshnessGrade.grade_1_poor) == 6


def test_hours_to_spoil_staples() -> None:
    """Grains and staples have longer shelf life (7 days for fresh)."""
    assert get_hours_to_spoil(FoodCategory.grains_staples, FreshnessGrade.grade_3_fresh) == 168


def test_v1_compatibility_grades() -> None:
    """Binary v1 grades ('fresh', 'spoiled') map cleanly to hours."""
    assert get_hours_to_spoil(FoodCategory.bread_bakery, FreshnessGrade.fresh) == 24
    assert get_hours_to_spoil(FoodCategory.bread_bakery, FreshnessGrade.spoiled) == 0


def test_calculate_expiry_timestamp() -> None:
    """calculate_expiry returns base_time + hours in UTC."""
    base = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    expiry = calculate_expiry(FoodCategory.dairy, FreshnessGrade.grade_3_fresh, base_time=base)
    expected = base + timedelta(hours=48)
    assert expiry == expected
    assert expiry.tzinfo == UTC


def test_calculate_expiry_defaults_to_now() -> None:
    """When base_time is None, calculate_expiry uses current UTC time."""
    before = datetime.now(UTC)
    expiry = calculate_expiry(FoodCategory.produce_vegetable, FreshnessGrade.grade_2_good)
    after = datetime.now(UTC)
    assert before + timedelta(hours=48) <= expiry <= after + timedelta(hours=48)
