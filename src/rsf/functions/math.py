"""Math intrinsic functions: States.MathRandom, States.MathAdd."""

from __future__ import annotations

import random

from rsf.functions.registry import intrinsic


@intrinsic("States.MathRandom")
def states_math_random(start: int, end: int) -> int:
    """Generate a random integer in [start, end]."""
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("States.MathRandom: both arguments must be integers")
    if start > end:
        raise ValueError("States.MathRandom: start must be <= end")
    return random.randint(start, end)


@intrinsic("States.MathAdd")
def states_math_add(a: int | float, b: int | float) -> int | float:
    """Add two numbers."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("States.MathAdd: both arguments must be numbers")
    result = a + b
    if isinstance(a, int) and isinstance(b, int):
        return int(result)
    return result
