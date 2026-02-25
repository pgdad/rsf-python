"""Utility intrinsic functions: States.UUID."""

from __future__ import annotations

import uuid

from rsf.functions.registry import intrinsic


@intrinsic("States.UUID")
def states_uuid() -> str:
    """Generate a UUID v4 string."""
    return str(uuid.uuid4())
