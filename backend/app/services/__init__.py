"""BountyLoop — Application services package."""

from app.services.cv_client import cv_client
from app.services.freshness_rules import calculate_expiry, get_hours_to_spoil
from app.services.impact import co2e_avoided, compute_donation_impact, meals_equivalent
from app.services.label_store import append_label_record
from app.services.storage import read_photo_bytes, save_donation_photo
from app.services.websocket_manager import ws_manager

__all__ = [
    "cv_client",
    "save_donation_photo",
    "read_photo_bytes",
    "get_hours_to_spoil",
    "calculate_expiry",
    "meals_equivalent",
    "co2e_avoided",
    "compute_donation_impact",
    "append_label_record",
    "ws_manager",
]
