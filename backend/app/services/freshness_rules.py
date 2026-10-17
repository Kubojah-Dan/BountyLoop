"""BountyLoop — Food Freshness & Expiry Rules Service.

Single source of truth for computing shelf-life hours and expires_at timestamps
based on food category and freshness assessment grade.
Also used downstream for matching urgency scoring.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.db.models.enums import FoodCategory, FreshnessGrade

logger = logging.getLogger(__name__)

# Default hours-to-spoil matrix: (FoodCategory, FreshnessGrade) -> hours
# Note: grade_0_spoiled / spoiled = 0 hours (immediate expiry / un-distributable)
DEFAULT_EXPIRY_HOURS: dict[str, dict[str, int]] = {
    FoodCategory.produce_fruit.value: {
        FreshnessGrade.grade_3_fresh.value: 72,
        FreshnessGrade.grade_2_good.value: 48,
        FreshnessGrade.grade_1_poor.value: 24,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 48,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.produce_vegetable.value: {
        FreshnessGrade.grade_3_fresh.value: 72,
        FreshnessGrade.grade_2_good.value: 48,
        FreshnessGrade.grade_1_poor.value: 24,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 48,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.bread_bakery.value: {
        FreshnessGrade.grade_3_fresh.value: 48,
        FreshnessGrade.grade_2_good.value: 24,
        FreshnessGrade.grade_1_poor.value: 12,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 24,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.dairy.value: {
        FreshnessGrade.grade_3_fresh.value: 48,
        FreshnessGrade.grade_2_good.value: 24,
        FreshnessGrade.grade_1_poor.value: 12,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 24,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.grains_staples.value: {
        FreshnessGrade.grade_3_fresh.value: 168,  # 7 days
        FreshnessGrade.grade_2_good.value: 96,  # 4 days
        FreshnessGrade.grade_1_poor.value: 48,  # 2 days
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 96,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.prepared_cooked.value: {
        FreshnessGrade.grade_3_fresh.value: 24,
        FreshnessGrade.grade_2_good.value: 12,
        FreshnessGrade.grade_1_poor.value: 6,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 12,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.meat_fish.value: {
        FreshnessGrade.grade_3_fresh.value: 24,
        FreshnessGrade.grade_2_good.value: 12,
        FreshnessGrade.grade_1_poor.value: 6,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 12,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.soup_stew.value: {
        FreshnessGrade.grade_3_fresh.value: 24,
        FreshnessGrade.grade_2_good.value: 12,
        FreshnessGrade.grade_1_poor.value: 6,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 12,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.dessert_bakery_sweet.value: {
        FreshnessGrade.grade_3_fresh.value: 48,
        FreshnessGrade.grade_2_good.value: 24,
        FreshnessGrade.grade_1_poor.value: 12,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 24,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.beverage.value: {
        FreshnessGrade.grade_3_fresh.value: 96,
        FreshnessGrade.grade_2_good.value: 48,
        FreshnessGrade.grade_1_poor.value: 24,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 48,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.condiment_sauce.value: {
        FreshnessGrade.grade_3_fresh.value: 168,
        FreshnessGrade.grade_2_good.value: 96,
        FreshnessGrade.grade_1_poor.value: 48,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 96,
        FreshnessGrade.spoiled.value: 0,
    },
    FoodCategory.other_unclassified.value: {
        FreshnessGrade.grade_3_fresh.value: 48,
        FreshnessGrade.grade_2_good.value: 24,
        FreshnessGrade.grade_1_poor.value: 12,
        FreshnessGrade.grade_0_spoiled.value: 0,
        FreshnessGrade.fresh.value: 24,
        FreshnessGrade.spoiled.value: 0,
    },
}


def get_hours_to_spoil(
    item: FoodCategory | str,
    freshness: FreshnessGrade | str,
) -> int:
    """Return remaining safe hours to spoil for a given food category and grade."""
    item_val = item.value if isinstance(item, FoodCategory) else str(item)
    fresh_val = freshness.value if isinstance(freshness, FreshnessGrade) else str(freshness)

    category_rules = DEFAULT_EXPIRY_HOURS.get(
        item_val, DEFAULT_EXPIRY_HOURS[FoodCategory.other_unclassified.value]
    )
    return category_rules.get(fresh_val, 24)


def calculate_expiry(
    item: FoodCategory | str,
    freshness: FreshnessGrade | str,
    base_time: datetime | None = None,
) -> datetime:
    """Calculate absolute expires_at timestamp in UTC."""
    if base_time is None:
        base_time = datetime.now(UTC)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=UTC)

    hours = get_hours_to_spoil(item, freshness)
    return base_time + timedelta(hours=hours)
