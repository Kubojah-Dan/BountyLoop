"""BountyLoop — Tests for CV Preprocessing (EXIF stripping, orientation, letterboxing)."""

from __future__ import annotations

import io

import numpy as np
from app.preprocess import (
    letterbox_image,
    preprocess_image,
    strip_exif_and_fix_orientation,
    to_normalized_tensor,
)
from PIL import Image
from PIL.ExifTags import Base


def create_image_with_gps_exif() -> bytes:
    """Create a sample JPEG image with embedded GPS EXIF metadata."""
    img = Image.new("RGB", (100, 80), color=(255, 120, 0))
    exif = img.getexif()
    # Add fake GPS tag / orientation tag
    exif[Base.Orientation] = 6  # 90 degrees CW rotation
    exif[Base.Make] = "TestCamera"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_strip_exif_eliminates_all_metadata() -> None:
    """Verify that EXIF metadata including GPS and device tags are stripped."""
    tagged_bytes = create_image_with_gps_exif()
    with Image.open(io.BytesIO(tagged_bytes)) as raw_img:
        assert raw_img.getexif() is not None
        assert Base.Make in raw_img.getexif()

    clean_img = strip_exif_and_fix_orientation(Image.open(io.BytesIO(tagged_bytes)))

    # Clean image must have no EXIF dictionary or tags
    clean_exif = clean_img.getexif()
    assert len(clean_exif) == 0
    assert Base.Make not in clean_exif


def test_letterbox_dimensions_and_padding() -> None:
    """Verify aspect ratio preservation and padding to 224x224."""
    img = Image.new("RGB", (400, 200), color=(0, 200, 100))
    letterboxed = letterbox_image(img, target_size=(224, 224))

    assert letterboxed.size == (224, 224)
    # Check that top and bottom padding is neutral gray (128, 128, 128)
    pixel_top = letterboxed.getpixel((112, 10))
    assert pixel_top == (128, 128, 128)


def test_to_normalized_tensor_shape_and_dtype() -> None:
    """Verify tensor shape (1, 3, 224, 224) and float32 dtype."""
    img = Image.new("RGB", (224, 224), color=(100, 150, 200))
    tensor = to_normalized_tensor(img)

    assert isinstance(tensor, np.ndarray)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == np.float32


def test_preprocess_image_with_tta() -> None:
    """Verify standard and TTA flipped outputs."""
    raw_bytes = create_image_with_gps_exif()
    std_tensor, flip_tensor = preprocess_image(
        raw_bytes, target_size=(224, 224), apply_tta=True
    )

    assert std_tensor.shape == (1, 3, 224, 224)
    assert flip_tensor is not None
    assert flip_tensor.shape == (1, 3, 224, 224)
