"""BountyLoop — Photo Storage & Server-Side Sanitization Service.

Saves uploaded donation photos to storage/photos/<donation_id>/<uuid>.jpg:
- Strips EXIF and GPS metadata server-side
- Corrects orientation using EXIF transpose before stripping
- Computes SHA-256 hash for duplicate detection
- Secure retrieval without path traversal
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

STORAGE_BASE_DIR = Path(os.environ.get("STORAGE_DIR", "storage"))
PHOTOS_DIR = STORAGE_BASE_DIR / "photos"


def init_storage() -> None:
    """Ensure base storage directories exist."""
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_and_hash_image(image_bytes: bytes) -> tuple[bytes, str]:
    """Sanitize image bytes: transpose orientation, strip EXIF metadata, and compute SHA-256.

    Returns:
        tuple[cleaned_bytes, sha256_hex]
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # 1. Transpose orientation if EXIF orientation exists
            img = ImageOps.exif_transpose(img)

            # 2. Convert to RGB (strips alpha channel and palette modes)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 3. Create a clean image copy without any metadata/EXIF dictionaries
            clean_img = Image.new("RGB", img.size)
            clean_img.putdata(list(img.getdata()))

            # 4. Save to buffer as clean JPEG with high quality
            out_buf = io.BytesIO()
            clean_img.save(out_buf, format="JPEG", quality=92, optimize=True)
            cleaned_bytes = out_buf.getvalue()

    except Exception as exc:
        logger.warning("Failed to parse and sanitize image bytes: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unreadable or corrupt image file.",
        ) from exc

    # 5. Compute SHA-256 hash of the cleaned image content
    sha256_hash = hashlib.sha256(cleaned_bytes).hexdigest()
    return cleaned_bytes, sha256_hash


def save_donation_photo(
    donation_id: uuid.UUID | str,
    image_bytes: bytes,
    photo_uuid: uuid.UUID | None = None,
) -> tuple[str, str]:
    """Sanitize and persist a donation photo on disk.

    Returns:
        tuple[relative_photo_path, sha256_hash]
    """
    cleaned_bytes, sha256_hash = sanitize_and_hash_image(image_bytes)

    if photo_uuid is None:
        photo_uuid = uuid.uuid4()

    donation_dir = PHOTOS_DIR / str(donation_id)
    donation_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{photo_uuid}.jpg"
    target_path = donation_dir / filename
    target_path.write_bytes(cleaned_bytes)

    # Return relative path for database storage: photos/<donation_id>/<photo_uuid>.jpg
    rel_path = f"photos/{donation_id}/{filename}"
    logger.info("Saved sanitized donation photo to %s (sha256: %s)", rel_path, sha256_hash[:12])
    return rel_path, sha256_hash


def read_photo_bytes(photo_path: str) -> bytes:
    """Read stored photo bytes securely, preventing path traversal."""
    # Normalize and verify within STORAGE_BASE_DIR
    target_path = (STORAGE_BASE_DIR / photo_path).resolve()
    base_resolved = STORAGE_BASE_DIR.resolve()

    if not str(target_path).startswith(str(base_resolved)):
        logger.warning("Path traversal attempt detected: %s", photo_path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to requested file path.",
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo file not found.",
        )

    return target_path.read_bytes()
