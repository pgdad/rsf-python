"""AnalyzeContent handler — simulates content analysis of an image."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)

# Simulated tag mapping by format
_FORMAT_TAGS = {
    "jpeg": ["photo", "landscape"],
    "png": ["graphic", "illustration"],
    "webp": ["photo", "optimized"],
    "gif": ["animation", "motion"],
}


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("AnalyzeContent")
def analyze_content(input_data: dict) -> dict:
    """Simulate content analysis of an image.

    Args:
        input_data: Image data with optional 'format' (str).

    Returns:
        dict with analyzed, tags, and confidence fields.
    """
    image_id = input_data.get("image_id")
    _log("AnalyzeContent", "Starting content analysis", image_id=image_id)

    fmt = input_data.get("format", "jpeg").lower()
    tags = _FORMAT_TAGS.get(fmt, ["image", "unknown"])
    confidence = 0.95

    _log(
        "AnalyzeContent",
        "Content analysis complete",
        image_id=image_id,
        tags=tags,
        confidence=confidence,
    )

    return {"analyzed": True, "tags": tags, "confidence": confidence}
