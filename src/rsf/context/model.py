"""ASL Context Object model.

The context object is accessible as $$ in JSONPath mode or $states.context in JSONata.
It provides runtime execution metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionContext:
    """Execution-level context."""

    Id: str = ""
    Input: Any = None
    Name: str = ""
    RoleArn: str = ""
    StartTime: str = ""
    RedriveCount: int = 0


@dataclass
class StateContext:
    """State-level context."""

    EnteredTime: str = ""
    Name: str = ""
    RetryCount: int = 0


@dataclass
class StateMachineContext:
    """State machine-level context."""

    Id: str = ""
    Name: str = ""


@dataclass
class TaskContext:
    """Task-level context (for callback patterns)."""

    Token: str = ""


@dataclass
class MapItemContext:
    """Map iteration item context."""

    Index: int = 0
    Key: str | None = None
    Value: Any = None
    Source: str = ""


@dataclass
class MapContext:
    """Map-level context."""

    Item: MapItemContext = field(default_factory=MapItemContext)


@dataclass
class ContextObject:
    """The complete ASL context object ($$).

    Provides runtime execution metadata accessible via $$ in JSONPath
    or $states.context in JSONata.
    """

    Execution: ExecutionContext = field(default_factory=ExecutionContext)
    State: StateContext = field(default_factory=StateContext)
    StateMachine: StateMachineContext = field(default_factory=StateMachineContext)
    Task: TaskContext = field(default_factory=TaskContext)
    Map: MapContext = field(default_factory=MapContext)

    @staticmethod
    def create(
        execution_id: str = "",
        execution_input: Any = None,
        execution_name: str = "",
        role_arn: str = "",
        state_name: str = "",
        state_machine_id: str = "",
        state_machine_name: str = "",
    ) -> ContextObject:
        """Create a ContextObject with common fields populated."""
        now = datetime.now(timezone.utc).isoformat()
        return ContextObject(
            Execution=ExecutionContext(
                Id=execution_id,
                Input=execution_input,
                Name=execution_name,
                RoleArn=role_arn,
                StartTime=now,
            ),
            State=StateContext(
                EnteredTime=now,
                Name=state_name,
            ),
            StateMachine=StateMachineContext(
                Id=state_machine_id,
                Name=state_machine_name,
            ),
        )
