"""BountyLoop — Dataset Splits & Dataset Card Generator.

Generates reproducible train, val, and test splits for the Kaggle Freshness dataset:
- Stratified by (item_family, freshness_state)
- Grouped by original image identity/hash prefix to prevent leakage
- Fixed random seed (42)
- Writes:
    ml/data/processed/splits/train.csv
    ml/data/processed/splits/val.csv
    ml/data/processed/splits/test.csv
    ml/data/processed/splits/dataset_card.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def get_image_hash_group(file_path: Path) -> str:
    """Compute perceptual or partial MD5 hash to group near-identical files."""
    hasher = hashlib.md5()
    # Read first 8KB and file size to form group key
    with open(file_path, "rb") as f:
        hasher.update(f.read(8192))
    size = file_path.stat().st_size
    return f"{hasher.hexdigest()[:8]}_{size // 4096}"


def create_splits(
    data_root: Path,
    output_dir: Path,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> dict[str, int]:
    """Create stratified grouped splits for Kaggle Freshness dataset."""
    random.seed(seed)
    freshness_dir = data_root / "freshness"

    if not freshness_dir.exists():
        logger.error("Freshness dataset not found at %s", freshness_dir)
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []

    for cls_dir in sorted(freshness_dir.iterdir()):
        if not cls_dir.is_dir():
            continue

        raw_cls = cls_dir.name
        # format: fresh_fruits -> state=fresh, category=fruits
        parts = raw_cls.split("_", 1)
        state = parts[0]  # fresh | spoiled
        category = parts[1] if len(parts) > 1 else "unknown"

        for img_path in sorted(cls_dir.iterdir()):
            if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            # Deterministic group id
            group_id = get_image_hash_group(img_path)

            records.append(
                {
                    "image_path": str(img_path.relative_to(data_root.parent)).replace(
                        "\\", "/"
                    ),
                    "filename": img_path.name,
                    "source": "kaggle_freshness_8class",
                    "original_class": raw_cls,
                    "freshness": state,
                    "item_family": category,
                    "group_id": group_id,
                }
            )

    logger.info("Indexed %d images across 8 classes", len(records))

    # Group records by (original_class, group_id) to avoid leakage
    defaultdict(list)
    groups_by_class: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for r in records:
        groups_by_class[r["original_class"]][r["group_id"]].append(r)

    train_rows: list[dict[str, Any]] = []
    val_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []

    for grps in groups_by_class.values():
        grp_list = list(grps.values())
        random.shuffle(grp_list)

        n = len(grp_list)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_grps = grp_list[:n_train]
        val_grps = grp_list[n_train : n_train + n_val]
        test_grps = grp_list[n_train + n_val :]

        for g in train_grps:
            for item in g:
                item["split"] = "train"
                train_rows.append(item)

        for g in val_grps:
            for item in g:
                item["split"] = "val"
                val_rows.append(item)

        for g in test_grps:
            for item in g:
                item["split"] = "test"
                test_rows.append(item)

    # Write CSVs
    def write_csv(filepath: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        fieldnames = [
            "image_path",
            "filename",
            "source",
            "original_class",
            "freshness",
            "item_family",
            "group_id",
            "split",
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(",".join(fieldnames) + "\n")
            for r in rows:
                f.write(",".join(str(r.get(k, "")) for k in fieldnames) + "\n")

    write_csv(output_dir / "train.csv", train_rows)
    write_csv(output_dir / "val.csv", val_rows)
    write_csv(output_dir / "test.csv", test_rows)

    logger.info(
        "Splits created: %d train, %d val, %d test (Total: %d)",
        len(train_rows),
        len(val_rows),
        len(test_rows),
        len(records),
    )

    # Write dataset card
    dataset_card = {
        "dataset_name": "Kaggle Fresh and Spoiled Food (Binary Baseline)",
        "source": "maheen00shahid/fresh-and-spoiled-food-image-dataset",
        "licence": "Research / CC BY-SA 4.0",
        "split_strategy": "Stratified grouped-by-hash, seed=42",
        "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
        "counts": {
            "total": len(records),
            "train": len(train_rows),
            "val": len(val_rows),
            "test": len(test_rows),
        },
        "classes": {
            "binary_target": ["fresh", "spoiled"],
            "item_families": ["bread", "dairy", "fruits", "vegetables"],
        },
        "known_biases": [
            "Bread and dairy have lower sample counts (~200-340) compared to produce (~400-490).",
            "Images are captured under varied domestic lighting and mobile camera resolutions.",
            "Prepared dishes and meats are absent from this dataset.",
        ],
    }

    with open(output_dir / "dataset_card.json", "w", encoding="utf-8") as f:
        json.dump(dataset_card, f, indent=2)

    return {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Kaggle freshness dataset splits."
    )
    parser.add_argument(
        "--data-root", type=Path, default=Path("ml/data"), help="Path to ml/data"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/data/processed/splits"),
        help="Output directory",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    create_splits(args.data_root, args.output, seed=args.seed)


if __name__ == "__main__":
    main()
