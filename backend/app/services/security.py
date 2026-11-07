"""BountyLoop — Security, Upload Validation & Circuit Breaker Services (Phase 12).

Implements:
1. Magic-byte MIME sniffing (JPEG, PNG, WebP) preventing renamed binary / script attacks.
2. File size enforcement (MAX_UPLOAD_MB -> 413 Payload Too Large).
3. Decompression-bomb guards (pixel count and dimension bounds).
4. Service-to-service authentication (INTERNAL_SERVICE_TOKEN).
5. CV-Service Circuit Breaker (graceful degradation to review queue during CV outage).
"""

from __future__ import annotations

import io
import logging
import time
from typing import Literal

from fastapi import Header, HTTPException, status
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger("bountyloop.security")
settings = get_settings()

# Magic bytes signatures
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"

# Decompression bomb safeguard
SAFE_MAX_PIXELS = 25_000_000  # 25 MP max
MAX_DIMENSION = 4096  # 4096 x 4096 max width/height
Image.MAX_IMAGE_PIXELS = SAFE_MAX_PIXELS


def validate_image_upload(
    file_bytes: bytes,
    filename: str = "upload.jpg",
    max_upload_mb: int | None = None,
) -> tuple[str, int, int]:
    """Validate uploaded image against file-size caps, magic bytes, and decompression bombs.

    Returns:
        tuple[mime_type, width, height]

    Raises:
        HTTPException(413): If file size exceeds MAX_UPLOAD_MB.
        HTTPException(400): If magic bytes do not match JPEG/PNG/WebP or image is corrupted/decompression bomb.
    """
    max_mb = max_upload_mb if max_upload_mb is not None else settings.max_upload_mb
    max_bytes = max_mb * 1024 * 1024

    # 1. Size cap check (413 Payload Too Large)
    file_size = len(file_bytes)
    if file_size > max_bytes:
        logger.warning(
            "Upload rejected: size %d bytes exceeds cap %d bytes (%d MB)",
            file_size,
            max_bytes,
            max_mb,
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image file exceeds maximum permitted upload size of {max_mb} MB.",
        )

    if file_size < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is too small to be a valid image.",
        )

    # 2. Magic byte sniffing (prevents renamed .txt / .sh / .exe files)
    detected_mime: str | None = None
    if file_bytes.startswith(JPEG_MAGIC):
        detected_mime = "image/jpeg"
    elif file_bytes.startswith(PNG_MAGIC):
        detected_mime = "image/png"
    elif file_bytes.startswith(RIFF_MAGIC) and WEBP_MAGIC in file_bytes[:16]:
        detected_mime = "image/webp"

    if detected_mime is None:
        logger.warning(
            "Magic byte check failed for '%s': signature does not match JPEG/PNG/WebP",
            filename,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid image format. File signature (magic bytes) does not match "
                "supported image types (JPEG, PNG, WebP). Renamed non-image files are rejected."
            ),
        )

    # 3. Decompression-bomb & dimension guard
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                logger.warning(
                    "Image dimension bounds exceeded (%dx%d > %d max)",
                    width,
                    height,
                    MAX_DIMENSION,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION} pixels.",
                )
            if (width * height) > SAFE_MAX_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image pixel area exceeds decompression safety limit.",
                )
    except Image.DecompressionBombError as exc:
        logger.error("Decompression bomb detected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decompression bomb detected. Image upload rejected for server security.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Pillow failed to parse sanitized image '%s': %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or unreadable image file.",
        ) from exc

    return detected_mime, width, height


def verify_internal_service_token(authorization: str | None = Header(None)) -> str:
    """Dependency ensuring caller possesses valid INTERNAL_SERVICE_TOKEN."""
    expected_token = settings.internal_service_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Bearer token required.",
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal service credentials.",
        )
    return token


class CVCircuitBreaker:
    """Circuit breaker for CV service calls.

    States:
    - CLOSED: Normal operation; requests pass through.
    - OPEN: Too many consecutive failures; requests short-circuit immediately.
    - HALF_OPEN: Recovery testing after timeout; one request allowed through.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.consecutive_failures = 0
        self.last_failure_time: float = 0.0
        self.state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"

    def is_available(self) -> bool:
        """Check if circuit breaker allows requests to proceed."""
        if self.state == "CLOSED":
            return True

        now = time.monotonic()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.recovery_timeout_seconds:
                logger.info("CV Circuit Breaker transitioning from OPEN to HALF_OPEN")
                self.state = "HALF_OPEN"
                return True
            return False

        # In HALF_OPEN, allow probe
        return True

    def record_success(self) -> None:
        """Record successful call, resetting circuit to CLOSED."""
        if self.state != "CLOSED":
            logger.info("CV Circuit Breaker reset to CLOSED after successful response")
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        """Record failed call, incrementing failure counter and potentially opening circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        if self.consecutive_failures >= self.failure_threshold:
            if self.state != "OPEN":
                logger.error(
                    "CV Circuit Breaker TRIPPED to OPEN (%d consecutive failures). "
                    "Next %ds of CV requests will degrade gracefully to human review.",
                    self.consecutive_failures,
                    int(self.recovery_timeout_seconds),
                )
            self.state = "OPEN"


cv_circuit_breaker = CVCircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30.0)
