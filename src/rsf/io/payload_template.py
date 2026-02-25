"""Payload template resolution for Parameters and ResultSelector.

Keys ending with '.$' are resolved:
- $.field → JSONPath reference into input
- $$.Execution.Id → Context object reference
- States.UUID() → Intrinsic function call
- Static keys pass through unchanged
"""

from __future__ import annotations

from typing import Any

from rsf.io.jsonpath import evaluate_jsonpath
from rsf.io.types import VariableStoreProtocol


def apply_payload_template(
    template: dict[str, Any],
    data: Any,
    context: Any | None = None,
    variables: VariableStoreProtocol | None = None,
    intrinsic_evaluator: Any | None = None,
) -> dict[str, Any]:
    """Resolve a payload template against input data.

    Keys ending with '.$' are dynamic references. The '.$' suffix is stripped
    from the output key, and the value is resolved:
    - JSONPath: $.field.subfield
    - Context: $$.Execution.Id
    - Intrinsic function: States.UUID()
    - Variable: $varName

    All other keys pass through with their values unchanged (but nested dicts
    are recursively resolved).
    """
    result: dict[str, Any] = {}
    for key, value in template.items():
        if key.endswith(".$"):
            # Dynamic reference — strip the .$ suffix
            output_key = key[:-2]
            resolved = _resolve_reference(
                value, data, context, variables, intrinsic_evaluator
            )
            result[output_key] = resolved
        else:
            # Static key — recurse into nested dicts
            if isinstance(value, dict):
                result[key] = apply_payload_template(
                    value, data, context, variables, intrinsic_evaluator
                )
            else:
                result[key] = value
    return result


def _resolve_reference(
    ref: str,
    data: Any,
    context: Any | None,
    variables: VariableStoreProtocol | None,
    intrinsic_evaluator: Any | None,
) -> Any:
    """Resolve a single dynamic reference value."""
    if not isinstance(ref, str):
        return ref

    # Intrinsic function call: States.xxx(...)
    if ref.startswith("States.") and "(" in ref:
        if intrinsic_evaluator is not None:
            return intrinsic_evaluator(ref, data, context, variables)
        raise ValueError(f"Intrinsic function call '{ref}' but no evaluator provided")

    # JSONPath or context reference
    return evaluate_jsonpath(data, ref, variables=variables, context=context)
