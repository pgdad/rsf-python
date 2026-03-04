"""ValidateImage handler — validates image format and size."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)

VALID_FORMATS = {"jpeg", "png", "webp", "gif"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class InvalidImageError(Exception):
    """Raised when the image data is invalid."""


@state("ValidateImage")
def validate_image(input_data: dict) -> dict:
    """Validate image format and size.

    Args:
        input_data: Image data with 'format' (str) and 'size_bytes' (int).

    Returns:
        dict with valid, format, and size_bytes fields.

    Raises:
        InvalidImageError: If format is unsupported or size exceeds limit.
    """
    _log("ValidateImage", "Starting image validation", image_id=input_data.get("image_id"))

    fmt = input_data.get("format", "").lower()
    size_bytes = input_data.get("size_bytes", 0)

    if fmt not in VALID_FORMATS:
        _log("ValidateImage", "Invalid image format", format=fmt)
        raise InvalidImageError(
            f"Unsupported image format: {fmt!r}. Supported formats: {sorted(VALID_FORMATS)}"
        )

    if size_bytes > MAX_SIZE_BYTES:
        _log("ValidateImage", "Image too large", size_bytes=size_bytes, max_bytes=MAX_SIZE_BYTES)
        raise InvalidImageError(
            f"Image size {size_bytes} bytes exceeds limit of {MAX_SIZE_BYTES} bytes (10 MB)"
        )

    _log("ValidateImage", "Image validated successfully", format=fmt, size_bytes=size_bytes)

    return {"valid": True, "format": fmt, "size_bytes": size_bytes}
