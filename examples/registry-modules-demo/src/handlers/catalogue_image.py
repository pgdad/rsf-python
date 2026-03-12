"""CatalogueImage handler — simulates cataloguing an image in the registry."""

import json
import logging
from datetime import datetime, timezone

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("CatalogueImage")
def catalogue_image(input_data: dict) -> dict:
    """Simulate cataloguing an image in the image registry.

    Args:
        input_data: Image data with 'image_id' (str).

    Returns:
        dict with catalogued, image_id, and timestamp fields.
    """
    image_id = input_data.get("image_id", "unknown")
    _log("CatalogueImage", "Starting image cataloguing", image_id=image_id)

    timestamp = datetime.now(timezone.utc).isoformat()

    _log("CatalogueImage", "Image catalogued successfully", image_id=image_id, timestamp=timestamp)

    return {"catalogued": True, "image_id": image_id, "timestamp": timestamp}
