"""Array intrinsic functions."""

from __future__ import annotations

from typing import Any

from rsf.functions.registry import intrinsic


@intrinsic("States.Array")
def states_array(*items: Any) -> list[Any]:
    """Create an array from arguments."""
    return list(items)


@intrinsic("States.ArrayPartition")
def states_array_partition(array: list, size: int) -> list[list]:
    """Split an array into chunks of the given size."""
    if not isinstance(array, list):
        raise TypeError("States.ArrayPartition: first argument must be an array")
    if not isinstance(size, int) or size <= 0:
        raise ValueError("States.ArrayPartition: size must be a positive integer")
    return [array[i : i + size] for i in range(0, len(array), size)]


@intrinsic("States.ArrayContains")
def states_array_contains(array: list, value: Any) -> bool:
    """Check if an array contains a value."""
    if not isinstance(array, list):
        raise TypeError("States.ArrayContains: first argument must be an array")
    return value in array


@intrinsic("States.ArrayRange")
def states_array_range(start: int, end: int, step: int) -> list[int]:
    """Generate a numeric range [start, end] with the given step."""
    if not all(isinstance(x, int) for x in (start, end, step)):
        raise TypeError("States.ArrayRange: all arguments must be integers")
    if step == 0:
        raise ValueError("States.ArrayRange: step cannot be zero")
    # ASL ArrayRange is inclusive of end
    result = []
    current = start
    if step > 0:
        while current <= end:
            result.append(current)
            current += step
    else:
        while current >= end:
            result.append(current)
            current += step
    return result


@intrinsic("States.ArrayGetItem")
def states_array_get_item(array: list, index: int) -> Any:
    """Get an item from an array by index."""
    if not isinstance(array, list):
        raise TypeError("States.ArrayGetItem: first argument must be an array")
    if not isinstance(index, int):
        raise TypeError("States.ArrayGetItem: second argument must be an integer")
    if index < 0 or index >= len(array):
        raise IndexError(f"States.ArrayGetItem: index {index} out of range")
    return array[index]


@intrinsic("States.ArrayLength")
def states_array_length(array: list) -> int:
    """Return the length of an array."""
    if not isinstance(array, list):
        raise TypeError("States.ArrayLength: argument must be an array")
    return len(array)


@intrinsic("States.ArrayUnique")
def states_array_unique(array: list) -> list:
    """Deduplicate an array, preserving order."""
    if not isinstance(array, list):
        raise TypeError("States.ArrayUnique: argument must be an array")
    seen: list = []
    for item in array:
        if item not in seen:
            seen.append(item)
    return seen
