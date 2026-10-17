"""BountyLoop — Active Learning & Retraining Label Store.

Appends confirmed donor corrections and adjudications to ml/data/custom/labels.csv
for continuous retraining and model performance evaluation (§5.7).
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Configurable path to retraining labels store
DEFAULT_LABEL_STORE_PATH = Path(os.environ.get("LABEL_STORE_PATH", "ml/data/custom/labels.csv"))

CSV_HEADERS = [
    "timestamp",
    "donation_id",
    "donor_id",
    "photo_path",
    "initial_item",
    "initial_freshness",
    "confirmed_item",
    "confirmed_freshness",
    "confirmed_weight_kg",
    "was_corrected",
]


def append_label_record(
    donation_id: str,
    donor_id: str,
    photo_path: str,
    initial_item: str,
    initial_freshness: str,
    confirmed_item: str,
    confirmed_freshness: str,
    confirmed_weight_kg: float,
    file_path: Path | None = None,
) -> None:
    """Append a confirmed or corrected donation label row to CSV."""
    if file_path is None:
        file_path = DEFAULT_LABEL_STORE_PATH

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = file_path.exists() and file_path.stat().st_size > 0

    was_corrected = initial_item != confirmed_item or initial_freshness != confirmed_freshness

    now_iso = datetime.now(UTC).isoformat()
    record = [
        now_iso,
        str(donation_id),
        str(donor_id),
        photo_path,
        initial_item,
        initial_freshness,
        confirmed_item,
        confirmed_freshness,
        f"{confirmed_weight_kg:.2f}",
        "true" if was_corrected else "false",
    ]

    try:
        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(CSV_HEADERS)
            writer.writerow(record)

        logger.info(
            "Logged label record for donation %s (corrected: %s) to %s",
            donation_id,
            was_corrected,
            file_path,
        )
    except Exception as exc:
        logger.error("Failed to append record to label store %s: %s", file_path, exc)
