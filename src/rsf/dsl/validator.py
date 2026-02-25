"""Semantic cross-state validation via BFS traversal.

Performs validations that Pydantic field-level validators cannot:
1. All Next/Default/Catch.Next references resolve to existing states
2. All states are reachable from StartAt (BFS)
3. At least one terminal state exists (Succeed, Fail, or End: true)
4. States.ALL must be last in Retry/Catch arrays
5. Recursive validation for Parallel branches and Map ItemProcessor
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from rsf.dsl.models import (
    BranchDefinition,
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
from rsf.dsl.choice import (
    BooleanAndRule,
    BooleanNotRule,
    BooleanOrRule,
    DataTestRule,
)
from rsf.dsl.errors import Catcher, RetryPolicy


@dataclass
class ValidationError:
    """A single semantic validation error."""

    message: str
    path: str = ""
    severity: str = "error"  # "error" or "warning"


def validate_definition(definition: StateMachineDefinition) -> list[ValidationError]:
    """Run all semantic validations on a parsed StateMachineDefinition.

    Returns a list of ValidationError instances (empty if valid).
    """
    errors: list[ValidationError] = []
    _validate_state_machine(
        states=definition.states,
        start_at=definition.start_at,
        path="",
        errors=errors,
    )
    return errors


def _validate_state_machine(
    states: dict[str, Any],
    start_at: str,
    path: str,
    errors: list[ValidationError],
) -> None:
    """Validate a state machine (top-level or branch)."""
    state_names = set(states.keys())

    # 1. StartAt must reference an existing state
    if start_at not in state_names:
        errors.append(
            ValidationError(
                message=f"StartAt '{start_at}' does not reference an existing state",
                path=f"{path}StartAt" if path else "StartAt",
            )
        )

    # 2. Validate all references resolve
    _validate_references(states, state_names, path, errors)

    # 3. Check reachability via BFS
    _validate_reachability(states, start_at, state_names, path, errors)

    # 4. Check at least one terminal state exists
    _validate_terminal_exists(states, path, errors)

    # 5. Validate States.ALL ordering in Retry/Catch arrays
    _validate_states_all_ordering(states, path, errors)

    # 6. Recurse into Parallel branches and Map ItemProcessor
    _validate_branches_recursive(states, path, errors)


def _validate_references(
    states: dict[str, Any],
    state_names: set[str],
    path: str,
    errors: list[ValidationError],
) -> None:
    """Check all Next, Default, and Catch.Next references resolve."""
    for name, state in states.items():
        state_path = f"{path}States.{name}"

        # Next field
        if hasattr(state, "next") and state.next is not None:
            if state.next not in state_names:
                errors.append(
                    ValidationError(
                        message=f"Next '{state.next}' does not reference an existing state",
                        path=f"{state_path}.Next",
                    )
                )

        # Choice state: Choices[].Next and Default
        if isinstance(state, ChoiceState):
            if state.default is not None and state.default not in state_names:
                errors.append(
                    ValidationError(
                        message=f"Default '{state.default}' does not reference an existing state",
                        path=f"{state_path}.Default",
                    )
                )
            for i, rule in enumerate(state.choices):
                _validate_choice_rule_references(
                    rule, state_names, f"{state_path}.Choices[{i}]", errors
                )

        # Catch handlers
        if hasattr(state, "catch") and state.catch:
            for i, catcher in enumerate(state.catch):
                if catcher.next not in state_names:
                    errors.append(
                        ValidationError(
                            message=f"Catch.Next '{catcher.next}' does not reference an existing state",
                            path=f"{state_path}.Catch[{i}].Next",
                        )
                    )


def _validate_choice_rule_references(
    rule: Any,
    state_names: set[str],
    path: str,
    errors: list[ValidationError],
) -> None:
    """Recursively validate references in choice rules."""
    if hasattr(rule, "next") and rule.next is not None:
        if rule.next not in state_names:
            errors.append(
                ValidationError(
                    message=f"Choice rule Next '{rule.next}' does not reference an existing state",
                    path=f"{path}.Next",
                )
            )
    # Recurse into boolean combinators
    if isinstance(rule, BooleanAndRule):
        for i, child in enumerate(rule.and_):
            _validate_choice_rule_references(
                child, state_names, f"{path}.And[{i}]", errors
            )
    elif isinstance(rule, BooleanOrRule):
        for i, child in enumerate(rule.or_):
            _validate_choice_rule_references(
                child, state_names, f"{path}.Or[{i}]", errors
            )
    elif isinstance(rule, BooleanNotRule):
        _validate_choice_rule_references(
            rule.not_, state_names, f"{path}.Not", errors
        )


def _validate_reachability(
    states: dict[str, Any],
    start_at: str,
    state_names: set[str],
    path: str,
    errors: list[ValidationError],
) -> None:
    """BFS from StartAt to check all states are reachable."""
    if start_at not in state_names:
        return  # Already reported as a StartAt error

    visited: set[str] = set()
    queue: deque[str] = deque([start_at])

    while queue:
        current = queue.popleft()
        if current in visited or current not in state_names:
            continue
        visited.add(current)
        state = states[current]

        # Collect all possible next states
        targets: list[str] = []

        if hasattr(state, "next") and state.next is not None:
            targets.append(state.next)

        if isinstance(state, ChoiceState):
            if state.default is not None:
                targets.append(state.default)
            for rule in state.choices:
                targets.extend(_collect_choice_rule_targets(rule))

        if hasattr(state, "catch") and state.catch:
            for catcher in state.catch:
                targets.append(catcher.next)

        for target in targets:
            if target not in visited:
                queue.append(target)

    unreachable = state_names - visited
    for name in sorted(unreachable):
        errors.append(
            ValidationError(
                message=f"State '{name}' is not reachable from StartAt",
                path=f"{path}States.{name}" if path else f"States.{name}",
            )
        )


def _collect_choice_rule_targets(rule: Any) -> list[str]:
    """Collect all Next targets from a choice rule recursively."""
    targets: list[str] = []
    if hasattr(rule, "next") and rule.next is not None:
        targets.append(rule.next)
    if isinstance(rule, BooleanAndRule):
        for child in rule.and_:
            targets.extend(_collect_choice_rule_targets(child))
    elif isinstance(rule, BooleanOrRule):
        for child in rule.or_:
            targets.extend(_collect_choice_rule_targets(child))
    elif isinstance(rule, BooleanNotRule):
        targets.extend(_collect_choice_rule_targets(rule.not_))
    return targets


def _validate_terminal_exists(
    states: dict[str, Any],
    path: str,
    errors: list[ValidationError],
) -> None:
    """Check that at least one terminal state exists."""
    has_terminal = False
    for state in states.values():
        if isinstance(state, (SucceedState, FailState)):
            has_terminal = True
            break
        if hasattr(state, "end") and state.end is True:
            has_terminal = True
            break

    if not has_terminal:
        errors.append(
            ValidationError(
                message="State machine must have at least one terminal state (Succeed, Fail, or End: true)",
                path=f"{path}States" if path else "States",
            )
        )


def _validate_states_all_ordering(
    states: dict[str, Any],
    path: str,
    errors: list[ValidationError],
) -> None:
    """Check that States.ALL is last in Retry and Catch arrays."""
    for name, state in states.items():
        state_path = f"{path}States.{name}" if path else f"States.{name}"

        if hasattr(state, "retry") and state.retry:
            for i, retry in enumerate(state.retry):
                if "States.ALL" in retry.error_equals and i < len(state.retry) - 1:
                    errors.append(
                        ValidationError(
                            message="States.ALL in Retry must be the last entry",
                            path=f"{state_path}.Retry[{i}]",
                        )
                    )

        if hasattr(state, "catch") and state.catch:
            for i, catcher in enumerate(state.catch):
                if "States.ALL" in catcher.error_equals and i < len(state.catch) - 1:
                    errors.append(
                        ValidationError(
                            message="States.ALL in Catch must be the last entry",
                            path=f"{state_path}.Catch[{i}]",
                        )
                    )


def _validate_branches_recursive(
    states: dict[str, Any],
    path: str,
    errors: list[ValidationError],
) -> None:
    """Recurse into Parallel branches and Map ItemProcessor."""
    for name, state in states.items():
        state_path = f"{path}States.{name}." if path else f"States.{name}."

        if isinstance(state, ParallelState):
            for i, branch in enumerate(state.branches):
                _validate_state_machine(
                    states=branch.states,
                    start_at=branch.start_at,
                    path=f"{state_path}Branches[{i}].",
                    errors=errors,
                )

        if isinstance(state, MapState) and state.item_processor is not None:
            _validate_state_machine(
                states=state.item_processor.states,
                start_at=state.item_processor.start_at,
                path=f"{state_path}ItemProcessor.",
                errors=errors,
            )
