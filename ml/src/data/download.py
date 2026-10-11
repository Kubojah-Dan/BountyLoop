"""BountyLoop — Dataset Download Helper.

Downloads required datasets from Kaggle / Mendeley when not already present.
Expects Kaggle API credentials configured via ~/.kaggle/kaggle.json or KAGGLE_USERNAME / KAGGLE_KEY.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KAGGLE_FRESHNESS_SLUG = "maheen00shahid/fresh-and-spoiled-food-image-dataset"
KAGGLE_FOOD101_SLUG = "kmader/food41"


def download_kaggle_dataset(slug: str, target_dir: Path) -> None:
    """Download and unzip a dataset using kaggle CLI or python API."""
    try:
        import kaggle  # type: ignore
    except ImportError:
        logger.error(
            "kaggle package not installed. Install with `pip install kaggle` and ensure kaggle.json is present."
        )
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s to %s...", slug, target_dir)
    kaggle.api.dataset_download_files(slug, path=str(target_dir), unzip=True)
    logger.info("Successfully downloaded and extracted %s", slug)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BountyLoop ML datasets.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("ml/data"),
        help="Root path for datasets",
    )
    args = parser.parse_args()

    freshness_dir = args.data_root / "raw" / "freshness"
    food101_dir = args.data_root / "raw" / "food101"

    if (args.data_root / "freshness").exists():
        logger.info(
            "Freshness dataset already present at %s", args.data_root / "freshness"
        )
    else:
        download_kaggle_dataset(KAGGLE_FRESHNESS_SLUG, freshness_dir)

    if (args.data_root / "food101").exists():
        logger.info("Food101 dataset already present at %s", args.data_root / "food101")
    else:
        download_kaggle_dataset(KAGGLE_FOOD101_SLUG, food101_dir)


if __name__ == "__main__":
    main()
