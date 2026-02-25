"""Intrinsic functions package — auto-registers all 18 functions on import."""

# Import all function modules to trigger @intrinsic decorator registration
from rsf.functions import array, encoding, json_funcs, math, string, utility
from rsf.functions.parser import IntrinsicParseError, evaluate_intrinsic
from rsf.functions.registry import (
    call_intrinsic,
    clear,
    get_intrinsic,
    intrinsic,
    registered_intrinsics,
)

__all__ = [
    "call_intrinsic",
    "clear",
    "evaluate_intrinsic",
    "get_intrinsic",
    "intrinsic",
    "IntrinsicParseError",
    "registered_intrinsics",
]
