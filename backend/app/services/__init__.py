"""BountyLoop — Application services package."""

from app.services.communication import COMMUNICATION_DISPATCH_LOG, communication_bus
from app.services.cv_client import cv_client
from app.services.forecast import (
    generate_batch_forecasts,
    generate_donor_forecasts,
    get_aggregate_forecast,
    get_donor_forecast,
    get_forecast_benchmark_metrics,
    trigger_forecast_prompts,
)
from app.services.freshness_rules import calculate_expiry, get_hours_to_spoil
from app.services.impact import (
    co2e_avoided,
    compute_donation_impact,
    generate_impact_csv,
    get_impact_factors_metadata,
    get_impact_summary,
    get_impact_timeseries,
    meals_equivalent,
    reconcile_impact,
)
from app.services.label_store import append_label_record
from app.services.notification import DISPATCHED_NOTIFICATIONS, notification_service
from app.services.sms import DISPATCHED_SMS, twilio_sms_client
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
    "get_impact_factors_metadata",
    "get_impact_summary",
    "get_impact_timeseries",
    "generate_impact_csv",
    "reconcile_impact",
    "generate_donor_forecasts",
    "get_donor_forecast",
    "get_aggregate_forecast",
    "generate_batch_forecasts",
    "get_forecast_benchmark_metrics",
    "trigger_forecast_prompts",
    "append_label_record",
    "ws_manager",
    "notification_service",
    "DISPATCHED_NOTIFICATIONS",
    "twilio_sms_client",
    "DISPATCHED_SMS",
    "communication_bus",
    "COMMUNICATION_DISPATCH_LOG",
]
