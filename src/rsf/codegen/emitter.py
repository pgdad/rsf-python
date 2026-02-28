"""Code emitter: generates Python code blocks for each state type.

Each state mapping is converted to a list of Python code lines that go
inside the while-loop state machine in the generated orchestrator.
"""

from __future__ import annotations

from typing import Any

from rsf.codegen.engine import topyrepr
from rsf.codegen.state_mappers import StateMapping


def emit_state_block(mapping: StateMapping, indent: int = 3) -> str:
    """Generate the Python code block for a single state.

    Args:
        mapping: The state mapping to emit code for.
        indent: Base indentation level (number of 4-space indents).

    Returns:
        A string of Python code lines for this state.
    """
    emitters = {
        "Task": _emit_task,
        "Pass": _emit_pass,
        "Choice": _emit_choice,
        "Wait": _emit_wait,
        "Succeed": _emit_succeed,
        "Fail": _emit_fail,
        "Parallel": _emit_parallel,
        "Map": _emit_map,
    }
    emitter = emitters.get(mapping.state_type)
    if emitter is None:
        raise ValueError(f"Unknown state type: {mapping.state_type}")

    lines = emitter(mapping)
    prefix = "    " * indent
    return "\n".join(f"{prefix}{line}" if line else "" for line in lines)


def _transition(params: dict[str, Any]) -> str:
    """Generate the transition line (next state or None)."""
    if params.get("next"):
        return f"current_state = {topyrepr(params['next'])}"
    return "current_state = None"


def _emit_task(mapping: StateMapping) -> list[str]:
    """Emit Task state code (context.step with optional catch)."""
    p = mapping.params
    name = topyrepr(mapping.state_name)
    lines: list[str] = []

    if p.get("has_catch"):
        lines.append("try:")
        lines.append(f"    handler = get_handler({name})")
        lines.append(f"    input_data = context.step({name}, handler, input_data)")
        lines.append(f"    {_transition(p)}")
        lines.append("except Exception as _err:")
        catch_policies = p.get("catch_policies", [])
        for i, cp in enumerate(catch_policies):
            kw = "if" if i == 0 else "elif"
            error_list = topyrepr(cp["error_equals"])
            lines.append(f'    {kw} type(_err).__name__ in {error_list} or "States.ALL" in {error_list}:')
            if cp.get("result_path"):
                lines.append(
                    f"        input_data = _apply_error_result(input_data, _err, {topyrepr(cp['result_path'])})"
                )
            lines.append(f"        current_state = {topyrepr(cp['next'])}")
        lines.append("    else:")
        lines.append("        raise")
    else:
        lines.append(f"handler = get_handler({name})")
        lines.append(f"input_data = context.step({name}, handler, input_data)")
        lines.append(_transition(p))

    return lines


def _emit_pass(mapping: StateMapping) -> list[str]:
    """Emit Pass state code (optional result injection)."""
    p = mapping.params
    lines: list[str] = []

    if "result" in p:
        result_repr = topyrepr(p["result"])
        if p.get("result_path"):
            lines.append(f"input_data = _apply_result_path(input_data, {result_repr}, {topyrepr(p['result_path'])})")
        else:
            lines.append(f"input_data = {result_repr}")
    lines.append(_transition(p))

    return lines


def _emit_choice(mapping: StateMapping) -> list[str]:
    """Emit Choice state code (conditional routing)."""
    p = mapping.params
    rules = p["rules"]
    lines: list[str] = []

    for i, rule in enumerate(rules):
        kw = "if" if i == 0 else "elif"
        condition = _build_condition(rule)
        lines.append(f"{kw} {condition}:")
        lines.append(f"    current_state = {topyrepr(rule['next'])}")

    if p.get("default"):
        lines.append("else:")
        lines.append(f"    current_state = {topyrepr(p['default'])}")

    return lines


def _build_condition(rule: dict[str, Any]) -> str:
    """Build a Python condition expression from a choice rule."""
    if rule["type"] == "data_test":
        return _build_data_test_condition(rule)
    elif rule["type"] == "and":
        sub = " and ".join(_build_condition(c) for c in rule["conditions"])
        return f"({sub})"
    elif rule["type"] == "or":
        sub = " or ".join(_build_condition(c) for c in rule["conditions"])
        return f"({sub})"
    elif rule["type"] == "not":
        sub = _build_condition(rule["condition"])
        return f"(not {sub})"
    else:
        raise ValueError(f"Unknown rule type: {rule['type']}")


def _build_data_test_condition(rule: dict[str, Any]) -> str:
    """Build a condition from a data test rule."""
    var = rule["variable"]
    op = rule["operator"]
    val = rule["value"]

    # Build the variable accessor
    accessor = _build_accessor(var)

    # Map operators to Python expressions
    if op in ("string_equals", "numeric_equals", "boolean_equals", "timestamp_equals"):
        return f"{accessor} == {topyrepr(val)}"
    elif op in ("string_equals_path", "numeric_equals_path", "boolean_equals_path", "timestamp_equals_path"):
        return f"{accessor} == _resolve_path(input_data, {topyrepr(val)})"
    elif op in ("string_greater_than", "numeric_greater_than", "timestamp_greater_than"):
        return f"{accessor} > {topyrepr(val)}"
    elif op in ("string_greater_than_path", "numeric_greater_than_path", "timestamp_greater_than_path"):
        return f"{accessor} > _resolve_path(input_data, {topyrepr(val)})"
    elif op in ("string_greater_than_equals", "numeric_greater_than_equals", "timestamp_greater_than_equals"):
        return f"{accessor} >= {topyrepr(val)}"
    elif op in (
        "string_greater_than_equals_path",
        "numeric_greater_than_equals_path",
        "timestamp_greater_than_equals_path",
    ):
        return f"{accessor} >= _resolve_path(input_data, {topyrepr(val)})"
    elif op in ("string_less_than", "numeric_less_than", "timestamp_less_than"):
        return f"{accessor} < {topyrepr(val)}"
    elif op in ("string_less_than_path", "numeric_less_than_path", "timestamp_less_than_path"):
        return f"{accessor} < _resolve_path(input_data, {topyrepr(val)})"
    elif op in ("string_less_than_equals", "numeric_less_than_equals", "timestamp_less_than_equals"):
        return f"{accessor} <= {topyrepr(val)}"
    elif op in ("string_less_than_equals_path", "numeric_less_than_equals_path", "timestamp_less_than_equals_path"):
        return f"{accessor} <= _resolve_path(input_data, {topyrepr(val)})"
    elif op == "string_matches":
        return f"_string_matches({accessor}, {topyrepr(val)})"
    elif op == "is_null":
        if val:
            return f"{accessor} is None"
        else:
            return f"{accessor} is not None"
    elif op == "is_present":
        # Check if the variable path exists in the data
        return f"_is_present(input_data, {topyrepr(var)})" if val else f"not _is_present(input_data, {topyrepr(var)})"
    elif op == "is_numeric":
        check = f"isinstance({accessor}, (int, float))"
        return check if val else f"not {check}"
    elif op == "is_string":
        check = f"isinstance({accessor}, str)"
        return check if val else f"not {check}"
    elif op == "is_boolean":
        check = f"isinstance({accessor}, bool)"
        return check if val else f"not {check}"
    elif op == "is_timestamp":
        return f"_is_timestamp({accessor})" if val else f"not _is_timestamp({accessor})"
    else:
        raise ValueError(f"Unknown operator: {op}")


def _build_accessor(variable: str) -> str:
    """Build a Python expression to access a JSONPath variable.

    Converts $.field.sub to input_data.get("field", {}).get("sub")
    or _resolve_path(input_data, "$.field.sub") for safety.
    """
    if variable == "$":
        return "input_data"
    # Use _resolve_path for deep access
    return f"_resolve_path(input_data, {topyrepr(variable)})"


def _emit_wait(mapping: StateMapping) -> list[str]:
    """Emit Wait state code (context.wait)."""
    p = mapping.params
    name = topyrepr(mapping.state_name)
    lines: list[str] = []

    if p.get("seconds") is not None:
        lines.append(f"context.wait({name}, Duration.seconds({p['seconds']}))")
    elif p.get("seconds_path") is not None:
        lines.append(f"_wait_seconds = _resolve_path(input_data, {topyrepr(p['seconds_path'])})")
        lines.append(f"context.wait({name}, Duration.seconds(_wait_seconds))")
    elif p.get("timestamp") is not None:
        lines.append(f"context.wait({name}, Duration.timestamp({topyrepr(p['timestamp'])}))")
    elif p.get("timestamp_path") is not None:
        lines.append(f"_wait_ts = _resolve_path(input_data, {topyrepr(p['timestamp_path'])})")
        lines.append(f"context.wait({name}, Duration.timestamp(_wait_ts))")

    lines.append(_transition(p))
    return lines


def _emit_succeed(mapping: StateMapping) -> list[str]:
    """Emit Succeed state code (return)."""
    return ["return input_data"]


def _emit_fail(mapping: StateMapping) -> list[str]:
    """Emit Fail state code (raise WorkflowError)."""
    p = mapping.params
    lines: list[str] = []

    if p.get("error"):
        error_repr = topyrepr(p["error"])
        cause_repr = topyrepr(p.get("cause"))
        lines.append(f"raise WorkflowError({error_repr}, {cause_repr})")
    elif p.get("error_path"):
        lines.append(f"_error = _resolve_path(input_data, {topyrepr(p['error_path'])})")
        if p.get("cause_path"):
            lines.append(f"_cause = _resolve_path(input_data, {topyrepr(p['cause_path'])})")
        else:
            lines.append(f"_cause = {topyrepr(p.get('cause'))}")
        lines.append("raise WorkflowError(_error, _cause)")
    else:
        lines.append('raise WorkflowError("UnknownError")')

    return lines


def _emit_parallel(mapping: StateMapping) -> list[str]:
    """Emit Parallel state code (context.parallel)."""
    p = mapping.params
    name = topyrepr(mapping.state_name)
    branches = p.get("branches", [])
    lines: list[str] = []

    # Build branch lambda list
    branch_lambdas = ", ".join(f"lambda _inp: _run_branch_{b['start_at'].lower()}(context, _inp)" for b in branches)

    if p.get("has_catch"):
        lines.append("try:")
        lines.append(f"    _branches = [{branch_lambdas}]")
        lines.append(f"    _result = context.parallel({name}, _branches, input_data)")
        lines.append("    input_data = _result.get_results()")
        lines.append(f"    {_transition(p)}")
        lines.append("except Exception as _err:")
        for i, cp in enumerate(p.get("catch_policies", [])):
            kw = "if" if i == 0 else "elif"
            error_list = topyrepr(cp["error_equals"])
            lines.append(f'    {kw} type(_err).__name__ in {error_list} or "States.ALL" in {error_list}:')
            if cp.get("result_path"):
                lines.append(
                    f"        input_data = _apply_error_result(input_data, _err, {topyrepr(cp['result_path'])})"
                )
            lines.append(f"        current_state = {topyrepr(cp['next'])}")
        lines.append("    else:")
        lines.append("        raise")
    else:
        lines.append(f"_branches = [{branch_lambdas}]")
        lines.append(f"_result = context.parallel({name}, _branches, input_data)")
        lines.append("input_data = _result.get_results()")
        lines.append(_transition(p))

    return lines


def _emit_map(mapping: StateMapping) -> list[str]:
    """Emit Map state code (context.map)."""
    p = mapping.params
    name = topyrepr(mapping.state_name)
    state_name_lower = mapping.state_name.lower()
    lines: list[str] = []

    max_conc = ""
    if p.get("max_concurrency") is not None:
        max_conc = f", max_concurrency={p['max_concurrency']}"

    if p.get("has_catch"):
        lines.append("try:")
        if p.get("items_path"):
            lines.append(f"    _items = _resolve_path(input_data, {topyrepr(p['items_path'])})")
        else:
            lines.append("    _items = input_data")
        _map_call = f"context.map({name}, lambda _item: _run_map_{state_name_lower}(context, _item), _items{max_conc})"
        lines.append(f"    _result = {_map_call}")
        lines.append("    input_data = _result.get_results()")
        lines.append(f"    {_transition(p)}")
        lines.append("except Exception as _err:")
        for i, cp in enumerate(p.get("catch_policies", [])):
            kw = "if" if i == 0 else "elif"
            error_list = topyrepr(cp["error_equals"])
            lines.append(f'    {kw} type(_err).__name__ in {error_list} or "States.ALL" in {error_list}:')
            if cp.get("result_path"):
                lines.append(
                    f"        input_data = _apply_error_result(input_data, _err, {topyrepr(cp['result_path'])})"
                )
            lines.append(f"        current_state = {topyrepr(cp['next'])}")
        lines.append("    else:")
        lines.append("        raise")
    else:
        if p.get("items_path"):
            lines.append(f"_items = _resolve_path(input_data, {topyrepr(p['items_path'])})")
        else:
            lines.append("_items = input_data")
        _map_call = f"context.map({name}, lambda _item: _run_map_{state_name_lower}(context, _item), _items{max_conc})"
        lines.append(f"_result = {_map_call}")
        lines.append("input_data = _result.get_results()")
        lines.append(_transition(p))

    return lines
