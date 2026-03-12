"""ResizeImage handler — simulates resizing an image to target dimensions."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("ResizeImage")
def resize_image(input_data: dict) -> dict:
    """Simulate resizing an image to target width, maintaining aspect ratio.

    Args:
        input_data: Image data with 'width' (int), 'height' (int),
                    and 'target_width' (int).

    Returns:
        dict with resized, original_width, original_height, target_width,
        and target_height fields.
    """
    image_id = input_data.get("image_id")
    _log("ResizeImage", "Starting image resize", image_id=image_id)

    original_width = input_data.get("width", 0)
    original_height = input_data.get("height", 0)
    target_width = input_data.get("target_width", original_width)

    # Compute target height maintaining aspect ratio
    if original_width > 0:
        ratio = target_width / original_width
        target_height = int(original_height * ratio)
    else:
        target_height = original_height

    _log(
        "ResizeImage",
        "Image resized successfully",
        image_id=image_id,
        original_width=original_width,
        original_height=original_height,
        target_width=target_width,
        target_height=target_height,
    )

    return {
        "resized": True,
        "original_width": original_width,
        "original_height": original_height,
        "target_width": target_width,
        "target_height": target_height,
    }
