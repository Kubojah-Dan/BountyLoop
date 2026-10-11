"""BountyLoop — Canonical database enums.

Aligned with the Master Implementation Plan (§5.2 taxonomy, §6 Phase 1 models).
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    """User account roles."""

    donor = "donor"
    recipient = "recipient"
    admin = "admin"
    volunteer = "volunteer"


class DonorKind(StrEnum):
    """Donor establishment categories."""

    restaurant = "restaurant"
    grocery = "grocery"
    farm = "farm"
    household = "household"
    other = "other"


class RecipientOrgType(StrEnum):
    """Recipient organization classifications."""

    food_bank = "food_bank"
    shelter = "shelter"
    community_fridge = "community_fridge"
    discount_buyer = "discount_buyer"


class FoodCategory(StrEnum):
    """12-category unified food rescue taxonomy (§5.2 Head A)."""

    produce_fruit = "produce_fruit"
    produce_vegetable = "produce_vegetable"
    bread_bakery = "bread_bakery"
    dairy = "dairy"
    grains_staples = "grains_staples"
    prepared_cooked = "prepared_cooked"
    meat_fish = "meat_fish"
    soup_stew = "soup_stew"
    dessert_bakery_sweet = "dessert_bakery_sweet"
    beverage = "beverage"
    condiment_sauce = "condiment_sauce"
    other_unclassified = "other_unclassified"


class FreshnessGrade(StrEnum):
    """Freshness assessment grades supporting v1 binary and v2 4-level scale (§5.2 Head B)."""

    fresh = "fresh"
    spoiled = "spoiled"
    grade_0_spoiled = "grade_0_spoiled"
    grade_1_poor = "grade_1_poor"
    grade_2_good = "grade_2_good"
    grade_3_fresh = "grade_3_fresh"


class HazardFlag(StrEnum):
    """Hazard safety gate (§5.2 Head C). Suspected flags require human review."""

    none = "none"
    suspected_contamination_or_formalin = "suspected_contamination_or_formalin"


class DonationStatus(StrEnum):
    """Lifecycle status of a food rescue donation."""

    draft = "draft"
    open = "open"
    matched = "matched"
    in_transit = "in_transit"
    completed = "completed"
    cancelled = "cancelled"
    expired = "expired"


class ClaimStatus(StrEnum):
    """Lifecycle status of a recipient claim."""

    offered = "offered"
    accepted = "accepted"
    declined = "declined"
    picked_up = "picked_up"
    failed = "failed"


class ReviewReason(StrEnum):
    """Trigger reasons for human review queue."""

    low_confidence = "low_confidence"
    hazard = "hazard"
    ambiguous_match = "ambiguous_match"
    other = "other"


class ReviewStatus(StrEnum):
    """Resolution status of review queue items."""

    pending = "pending"
    resolved = "resolved"
