"""BountyLoop — Food-101 Unpacker & Verifier.

Extracts Food-101 images from HDF5 bundles or verifies existing extracted images
into ml/data/processed/food101/<class_name>/<idx>.jpg.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def verify_or_unpack_food101(source_dir: Path, output_dir: Path) -> int:
    """Verify extracted images or unpack HDF5 archive if needed."""
    images_dir = source_dir / "images"
    if images_dir.exists() and any(images_dir.iterdir()):
        logger.info("Found pre-extracted Food-101 images at %s", images_dir)
        class_folders = [p for p in images_dir.iterdir() if p.is_dir()]
        total_images = sum(len(list(cf.glob("*.jpg"))) for cf in class_folders)
        logger.info(
            "Verified %d classes and %d total images", len(class_folders), total_images
        )
        return total_images

    # If images directory is not present, check for HDF5 bundles
    h5_files = list(source_dir.glob("*.h5"))
    if not h5_files:
        logger.warning("No images directory or .h5 files found in %s", source_dir)
        return 0

    try:
        import h5py  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        logger.error(
            "h5py and pillow are required to unpack HDF5 files. Install them to continue."
        )
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Unpacking HDF5 files from %s to %s...", source_dir, output_dir)
    # Target full resolution H5 if available
    largest_h5 = max(h5_files, key=lambda f: f.stat().st_size)
    logger.info("Reading HDF5 bundle: %s", largest_h5.name)

    with h5py.File(largest_h5, "r") as hf:
        keys = list(hf.keys())
        logger.info("HDF5 keys available: %s", keys)
        # Handle typical image and label datasets
        if "images" in hf and "category_names" in hf:
            imgs = hf["images"]
            cats = hf["category_names"]
            for i in range(len(imgs)):
                cat_name = (
                    cats[i].decode("utf-8")
                    if isinstance(cats[i], bytes)
                    else str(cats[i])
                )
                cat_folder = output_dir / cat_name
                cat_folder.mkdir(parents=True, exist_ok=True)
                img_arr = imgs[i]
                img = Image.fromarray(img_arr)
                img.save(cat_folder / f"{i:06d}.jpg", quality=90)
                if (i + 1) % 5000 == 0:
                    logger.info("Unpacked %d images...", i + 1)

    return len(list(output_dir.rglob("*.jpg")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Unpack or verify Food-101 dataset.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("ml/data/food101"),
        help="Source directory containing food101 images or .h5 files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/data/processed/food101"),
        help="Output directory for unpacked images",
    )
    args = parser.parse_args()
    verify_or_unpack_food101(args.source, args.output)


if __name__ == "__main__":
    main()
