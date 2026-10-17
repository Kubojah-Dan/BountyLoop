"""BountyLoop — Unit Tests for Photo Storage & Sanitization."""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi import HTTPException
from PIL import Image

from app.services.storage import (
    read_photo_bytes,
    sanitize_and_hash_image,
    save_donation_photo,
)


def create_sample_jpeg_bytes(width: int = 100, height: int = 100, color=(150, 75, 50)) -> bytes:
    """Generate in-memory JPEG test image."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_sanitize_and_hash_image() -> None:
    """Valid image bytes are converted to clean JPEG and hashed with SHA-256."""
    raw_bytes = create_sample_jpeg_bytes()
    clean_bytes, sha256_hash = sanitize_and_hash_image(raw_bytes)

    assert len(clean_bytes) > 0
    assert len(sha256_hash) == 64  # SHA-256 hex string

    # Verify that clean_bytes can be opened and contains no EXIF
    with Image.open(io.BytesIO(clean_bytes)) as img:
        assert img.format == "JPEG"
        assert img.size == (100, 100)
        exif = img.getexif()
        assert len(exif) == 0


def test_sanitize_corrupt_bytes_raises_400() -> None:
    """Non-image bytes raise 400 Bad Request."""
    corrupt_bytes = b"NOT_AN_IMAGE_FILE_DATA_12345"
    with pytest.raises(HTTPException) as exc_info:
        sanitize_and_hash_image(corrupt_bytes)
    assert exc_info.value.status_code == 400


def test_save_donation_photo(tmp_path, monkeypatch) -> None:
    """save_donation_photo persists file to storage/photos/<donation_id>/<uuid>.jpg."""
    monkeypatch.setattr("app.services.storage.STORAGE_BASE_DIR", tmp_path)
    monkeypatch.setattr("app.services.storage.PHOTOS_DIR", tmp_path / "photos")

    donation_id = uuid.uuid4()
    raw_bytes = create_sample_jpeg_bytes()
    rel_path, sha256_hash = save_donation_photo(donation_id, raw_bytes)

    assert rel_path.startswith(f"photos/{donation_id}/")
    saved_file = tmp_path / rel_path
    assert saved_file.exists()
    assert saved_file.is_file()

    # Read photo back
    read_bytes = read_photo_bytes(rel_path)
    assert len(read_bytes) == len(saved_file.read_bytes())


def test_read_photo_path_traversal_blocked(tmp_path, monkeypatch) -> None:
    """Path traversal attempts raise 403 Forbidden."""
    monkeypatch.setattr("app.services.storage.STORAGE_BASE_DIR", tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        read_photo_bytes("../../etc/passwd")
    assert exc_info.value.status_code == 403


def test_read_photo_non_existent_raises_404(tmp_path, monkeypatch) -> None:
    """Missing photo raises 404 Not Found."""
    monkeypatch.setattr("app.services.storage.STORAGE_BASE_DIR", tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        read_photo_bytes(f"photos/{uuid.uuid4()}/missing.jpg")
    assert exc_info.value.status_code == 404
