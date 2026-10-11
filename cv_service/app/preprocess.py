"""BountyLoop — Computer Vision Preprocessing Pipeline.

Handles:
1. EXIF stripping (privacy protection: eliminates GPS, device, timestamp tags)
2. EXIF orientation correction (auto-rotation before stripping)
3. Letterbox resizing (aspect-ratio preserving resize to target dimensions)
4. Normalization (ImageNet mean/std)
5. Test-time augmentation (TTA: horizontal flip)
"""

from __future__ import annotations

import io
import logging

import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def strip_exif_and_fix_orientation(image: Image.Image) -> Image.Image:
    """Correct orientation using EXIF if present, then strip all EXIF/GPS tags."""
    try:
        # Transpose image based on EXIF orientation
        image = ImageOps.exif_transpose(image)
    except (ValueError, OSError, TypeError) as e:
        logger.debug("No valid EXIF orientation tag found or error transposing: %s", e)

    # Convert to RGB (dropping palette, alpha channels, etc.)
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Create brand new clean image without EXIF dictionary
    clean_image = Image.new("RGB", image.size)
    clean_image.paste(image)
    return clean_image


def letterbox_image(
    image: Image.Image, target_size: tuple[int, int] = (224, 224)
) -> Image.Image:
    """Resize image maintaining aspect ratio and pad with neutral gray (128, 128, 128)."""
    target_w, target_h = target_size
    orig_w, orig_h = image.size

    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)

    # Create padded background
    canvas = Image.new("RGB", target_size, (128, 128, 128))
    pad_left = (target_w - new_w) // 2
    pad_top = (target_h - new_h) // 2
    canvas.paste(resized, (pad_left, pad_top))
    return canvas


def to_normalized_tensor(image: Image.Image) -> np.ndarray:
    """Convert PIL image to normalized float32 tensor of shape (1, 3, H, W)."""
    arr = np.array(image, dtype=np.float32) / 255.0  # (H, W, 3)
    normalized = (arr - IMAGENET_MEAN) / IMAGENET_STD
    chw = np.transpose(normalized, (2, 0, 1))  # (3, H, W)
    batch = np.expand_dims(chw, axis=0)  # (1, 3, H, W)
    return batch.astype(np.float32)


def preprocess_image(
    image_bytes: bytes,
    target_size: tuple[int, int] = (224, 224),
    apply_tta: bool = False,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Preprocess raw image bytes into normalized tensors for model inference.

    Returns:
        (standard_tensor, flipped_tensor_if_tta)
    """
    with Image.open(io.BytesIO(image_bytes)) as raw_img:
        clean_img = strip_exif_and_fix_orientation(raw_img)

    letterboxed = letterbox_image(clean_img, target_size=target_size)
    standard_tensor = to_normalized_tensor(letterboxed)

    flipped_tensor = None
    if apply_tta:
        flipped_img = letterboxed.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        flipped_tensor = to_normalized_tensor(flipped_img)

    return standard_tensor, flipped_tensor
