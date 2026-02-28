"""BFS traversal and SDK primitive mapping for all 8 state types.

Walks a StateMachineDefinition from StartAt, collecting every reachable state
and mapping it to the appropriate Lambda Durable Functions SDK primitive.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from rsf.dsl.choice import (
    BooleanAndRule,
    BooleanNotRule,
    BooleanOrRule,
    DataTestRule,
)
from rsf.dsl.models import (
    ChoiceState,
    FailState,
    MapState,
    ParallelState,
    PassState,
    StateMachineDefinition,
    SucceedState,
    TaskState,
    WaitState,
)


@dataclass
class StateMapping:
    """Maps a single DSL state to its SDK primitive and parameters."""

    state_name: str
    state_type: str  # Task, Pass, Choice, Wait, Succeed, Fail, Parallel, Map
    # context.step, context.wait, conditional, passthrough, return, raise, context.parallel, context.map
    sdk_primitive: str
    params: dict[str, Any] = field(default_factory=dict)


def map_states(definition: StateMachineDefinition) -> list[StateMapping]:
    """BFS traversal from StartAt, mapping all reachable states to SDK primitives.

    Returns an ordered list of StateMapping instances in BFS visit order.
    """
    mappings: list[StateMapping] = []
    visited: set[str] = set()
    queue: deque[str] = deque([definition.start_at])

    while queue:
        name = queue.popleft()
        if name in visited or name not in definition.states:
            continue
        visited.add(name)

        state = definition.states[name]
        mapping = _map_single_state(name, state)
        mappings.append(mapping)

        # Enqueue all reachable next states
        for target in _collect_targets(state):
            if target not in visited:
                queue.append(target)

    return mappings


def _map_single_state(name: str, state: Any) -> StateMapping:
    """Map a single state to its SDK primitive."""
    if isinstance(state, TaskState):
        return _map_task(name, state)
    elif isinstance(state, PassState):
        return _map_pass(name, state)
    elif isinstance(state, ChoiceState):
        return _map_choice(name, state)
    elif isinstance(state, WaitState):
        return _map_wait(name, state)
    elif isinstance(state, SucceedState):
        return _map_succeed(name, state)
    elif isinstance(state, FailState):
        return _map_fail(name, state)
    elif isinstance(state, ParallelState):
        return _map_parallel(name, state)
    elif isinstance(state, MapState):
        return _map_map(name, state)
    else:
        raise ValueError(f"Unknown state type for '{name}': {type(state)}")


def _map_task(name: str, state: TaskState) -> StateMapping:
    """Map a Task state to context.step."""
    params: dict[str, Any] = {
        "next": state.next,
        "end": state.end,
    }
    if state.timeout_seconds is not None:
        params["timeout_seconds"] = state.timeout_seconds
    if state.timeout_seconds_path is not None:
        params["timeout_seconds_path"] = state.timeout_seconds_path
    if state.heartbeat_seconds is not None:
        params["heartbeat_seconds"] = state.heartbeat_seconds
    if state.heartbeat_seconds_path is not None:
        params["heartbeat_seconds_path"] = state.heartbeat_seconds_path
    if state.retry:
        params["has_retry"] = True
        params["retry_policies"] = [
            {
                "error_equals": r.error_equals,
                "interval_seconds": r.interval_seconds,
                "max_attempts": r.max_attempts,
                "backoff_rate": r.backoff_rate,
            }
            for r in state.retry
        ]
    if state.catch:
        params["has_catch"] = True
        params["catch_policies"] = [
            {
                "error_equals": c.error_equals,
                "next": c.next,
                "result_path": c.result_path,
            }
            for c in state.catch
        ]
    return StateMapping(
        state_name=name,
        state_type="Task",
        sdk_primitive="context.step",
        params=params,
    )


def _map_pass(name: str, state: PassState) -> StateMapping:
    """Map a Pass state to passthrough."""
    params: dict[str, Any] = {
        "next": state.next,
        "end": state.end,
    }
    if state.result is not None:
        params["result"] = state.result
    if state.result_path is not None:
        params["result_path"] = state.result_path
    return StateMapping(
        state_name=name,
        state_type="Pass",
        sdk_primitive="passthrough",
        params=params,
    )


def _map_choice(name: str, state: ChoiceState) -> StateMapping:
    """Map a Choice state to conditional routing."""
    rules = [_map_choice_rule(rule) for rule in state.choices]
    params: dict[str, Any] = {
        "rules": rules,
        "default": state.default,
    }
    return StateMapping(
        state_name=name,
        state_type="Choice",
        sdk_primitive="conditional",
        params=params,
    )


def _map_choice_rule(rule: Any) -> dict[str, Any]:
    """Recursively map a choice rule to a dict representation."""
    if isinstance(rule, DataTestRule):
        # Find which operator is set
        operator = None
        value = None
        for op in (
            "string_equals",
            "string_equals_path",
            "string_greater_than",
            "string_greater_than_path",
            "string_greater_than_equals",
            "string_greater_than_equals_path",
            "string_less_than",
            "string_less_than_path",
            "string_less_than_equals",
            "string_less_than_equals_path",
            "string_matches",
            "numeric_equals",
            "numeric_equals_path",
            "numeric_greater_than",
            "numeric_greater_than_path",
            "numeric_greater_than_equals",
            "numeric_greater_than_equals_path",
            "numeric_less_than",
            "numeric_less_than_path",
            "numeric_less_than_equals",
            "numeric_less_than_equals_path",
            "boolean_equals",
            "boolean_equals_path",
            "timestamp_equals",
            "timestamp_equals_path",
            "timestamp_greater_than",
            "timestamp_greater_than_path",
            "timestamp_greater_than_equals",
            "timestamp_greater_than_equals_path",
            "timestamp_less_than",
            "timestamp_less_than_path",
            "timestamp_less_than_equals",
            "timestamp_less_than_equals_path",
            "is_null",
            "is_present",
            "is_numeric",
            "is_string",
            "is_boolean",
            "is_timestamp",
        ):
            val = getattr(rule, op, None)
            if val is not None:
                operator = op
                value = val
                break
        return {
            "type": "data_test",
            "variable": rule.variable,
            "operator": operator,
            "value": value,
            "next": rule.next,
        }
    elif isinstance(rule, BooleanAndRule):
        return {
            "type": "and",
            "conditions": [_map_choice_rule(r) for r in rule.and_],
            "next": rule.next,
        }
    elif isinstance(rule, BooleanOrRule):
        return {
            "type": "or",
            "conditions": [_map_choice_rule(r) for r in rule.or_],
            "next": rule.next,
        }
    elif isinstance(rule, BooleanNotRule):
        return {
            "type": "not",
            "condition": _map_choice_rule(rule.not_),
            "next": rule.next,
        }
    else:
        raise ValueError(f"Unknown choice rule type: {type(rule)}")


def _map_wait(name: str, state: WaitState) -> StateMapping:
    """Map a Wait state to context.wait."""
    params: dict[str, Any] = {
        "next": state.next,
        "end": state.end,
    }
    if state.seconds is not None:
        params["seconds"] = state.seconds
    if state.timestamp is not None:
        params["timestamp"] = state.timestamp
    if state.seconds_path is not None:
        params["seconds_path"] = state.seconds_path
    if state.timestamp_path is not None:
        params["timestamp_path"] = state.timestamp_path
    return StateMapping(
        state_name=name,
        state_type="Wait",
        sdk_primitive="context.wait",
        params=params,
    )


def _map_succeed(name: str, state: SucceedState) -> StateMapping:
    """Map a Succeed state to return."""
    return StateMapping(
        state_name=name,
        state_type="Succeed",
        sdk_primitive="return",
        params={},
    )


def _map_fail(name: str, state: FailState) -> StateMapping:
    """Map a Fail state to raise WorkflowError."""
    params: dict[str, Any] = {}
    if state.error is not None:
        params["error"] = state.error
    if state.error_path is not None:
        params["error_path"] = state.error_path
    if state.cause is not None:
        params["cause"] = state.cause
    if state.cause_path is not None:
        params["cause_path"] = state.cause_path
    return StateMapping(
        state_name=name,
        state_type="Fail",
        sdk_primitive="raise",
        params=params,
    )


def _map_parallel(name: str, state: ParallelState) -> StateMapping:
    """Map a Parallel state to context.parallel."""
    branches = []
    for branch in state.branches:
        branches.append(
            {
                "start_at": branch.start_at,
                "states": list(branch.states.keys()),
            }
        )
    params: dict[str, Any] = {
        "next": state.next,
        "end": state.end,
        "branches": branches,
    }
    if state.retry:
        params["has_retry"] = True
        params["retry_policies"] = [
            {
                "error_equals": r.error_equals,
                "interval_seconds": r.interval_seconds,
                "max_attempts": r.max_attempts,
                "backoff_rate": r.backoff_rate,
            }
            for r in state.retry
        ]
    if state.catch:
        params["has_catch"] = True
        params["catch_policies"] = [
            {
                "error_equals": c.error_equals,
                "next": c.next,
                "result_path": c.result_path,
            }
            for c in state.catch
        ]
    return StateMapping(
        state_name=name,
        state_type="Parallel",
        sdk_primitive="context.parallel",
        params=params,
    )


def _map_map(name: str, state: MapState) -> StateMapping:
    """Map a Map state to context.map."""
    params: dict[str, Any] = {
        "next": state.next,
        "end": state.end,
    }
    if state.items_path is not None:
        params["items_path"] = state.items_path
    if state.max_concurrency is not None:
        params["max_concurrency"] = state.max_concurrency
    if state.item_processor is not None:
        params["item_processor"] = {
            "start_at": state.item_processor.start_at,
            "states": list(state.item_processor.states.keys()),
        }
    if state.retry:
        params["has_retry"] = True
    if state.catch:
        params["has_catch"] = True
        params["catch_policies"] = [
            {
                "error_equals": c.error_equals,
                "next": c.next,
                "result_path": c.result_path,
            }
            for c in state.catch
        ]
    return StateMapping(
        state_name=name,
        state_type="Map",
        sdk_primitive="context.map",
        params=params,
    )


def _collect_targets(state: Any) -> list[str]:
    """Collect all possible next-state names from a state."""
    targets: list[str] = []

    # Next field (Task, Pass, Wait, Parallel, Map)
    if hasattr(state, "next") and state.next is not None:
        targets.append(state.next)

    # Choice state: all rule targets + Default
    if isinstance(state, ChoiceState):
        if state.default is not None:
            targets.append(state.default)
        for rule in state.choices:
            targets.extend(_collect_rule_targets(rule))

    # Catch handlers
    if hasattr(state, "catch") and state.catch:
        for catcher in state.catch:
            targets.append(catcher.next)

    return targets


def _collect_rule_targets(rule: Any) -> list[str]:
    """Recursively collect Next targets from choice rules."""
    targets: list[str] = []
    if hasattr(rule, "next") and rule.next is not None:
        targets.append(rule.next)
    if isinstance(rule, BooleanAndRule):
        for child in rule.and_:
            targets.extend(_collect_rule_targets(child))
    elif isinstance(rule, BooleanOrRule):
        for child in rule.or_:
            targets.extend(_collect_rule_targets(child))
    elif isinstance(rule, BooleanNotRule):
        targets.extend(_collect_rule_targets(rule.not_))
    return targets
