"""Pydantic v2 models for all 8 ASL state types and the root StateMachineDefinition."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from rsf.dsl.choice import ChoiceRule
from rsf.dsl.errors import Catcher, RetryPolicy
from rsf.dsl.types import ProcessorMode, QueryLanguage


class _IOFields(BaseModel):
    """Mixin for I/O processing fields shared by multiple state types."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    input_path: str | None = Field(default=None, alias="InputPath")
    output_path: str | None = Field(default=None, alias="OutputPath")
    parameters: dict[str, Any] | None = Field(default=None, alias="Parameters")
    result_selector: dict[str, Any] | None = Field(default=None, alias="ResultSelector")
    result_path: str | None = Field(default=None, alias="ResultPath")


class _TransitionFields(BaseModel):
    """Mixin for Next/End transition fields."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    next: str | None = Field(default=None, alias="Next")
    end: bool | None = Field(default=None, alias="End")

    @model_validator(mode="after")
    def next_xor_end(self) -> "_TransitionFields":
        if self.next is not None and self.end is True:
            raise ValueError("Cannot specify both Next and End")
        if self.next is None and self.end is not True:
            raise ValueError("Must specify either Next or End: true")
        return self


class _AssignOutput(BaseModel):
    """Mixin for Assign and Output fields (variables support)."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    assign: dict[str, Any] | None = Field(default=None, alias="Assign")
    output: Any | None = Field(default=None, alias="Output")


class TaskState(_IOFields, _TransitionFields, _AssignOutput):
    """Task state — executes a handler function."""

    type: Literal["Task"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")

    timeout_seconds: int | None = Field(default=None, alias="TimeoutSeconds", ge=0)
    timeout_seconds_path: str | None = Field(default=None, alias="TimeoutSecondsPath")
    heartbeat_seconds: int | None = Field(default=None, alias="HeartbeatSeconds", ge=0)
    heartbeat_seconds_path: str | None = Field(default=None, alias="HeartbeatSecondsPath")

    retry: list[RetryPolicy] | None = Field(default=None, alias="Retry")
    catch: list[Catcher] | None = Field(default=None, alias="Catch")

    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")

    @model_validator(mode="after")
    def timeout_mutual_exclusion(self) -> "TaskState":
        if self.timeout_seconds is not None and self.timeout_seconds_path is not None:
            raise ValueError("Cannot specify both TimeoutSeconds and TimeoutSecondsPath")
        if self.heartbeat_seconds is not None and self.heartbeat_seconds_path is not None:
            raise ValueError("Cannot specify both HeartbeatSeconds and HeartbeatSecondsPath")
        # Heartbeat must be less than timeout (when both are static values)
        if (
            self.heartbeat_seconds is not None
            and self.timeout_seconds is not None
            and self.heartbeat_seconds >= self.timeout_seconds
        ):
            raise ValueError("HeartbeatSeconds must be less than TimeoutSeconds")
        return self


class PassState(_IOFields, _TransitionFields, _AssignOutput):
    """Pass state — passes input to output, optionally injecting a Result."""

    type: Literal["Pass"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")
    result: Any | None = Field(default=None, alias="Result")
    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")


class ChoiceState(BaseModel):
    """Choice state — branches based on conditions."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    type: Literal["Choice"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")
    choices: list[ChoiceRule] = Field(alias="Choices")
    default: str | None = Field(default=None, alias="Default")

    input_path: str | None = Field(default=None, alias="InputPath")
    output_path: str | None = Field(default=None, alias="OutputPath")
    assign: dict[str, Any] | None = Field(default=None, alias="Assign")
    output: Any | None = Field(default=None, alias="Output")
    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")


class WaitState(_IOFields, _TransitionFields, _AssignOutput):
    """Wait state — delays execution."""

    type: Literal["Wait"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")

    seconds: int | None = Field(default=None, alias="Seconds", ge=0)
    timestamp: str | None = Field(default=None, alias="Timestamp")
    seconds_path: str | None = Field(default=None, alias="SecondsPath")
    timestamp_path: str | None = Field(default=None, alias="TimestampPath")

    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")

    @model_validator(mode="after")
    def exactly_one_wait_spec(self) -> "WaitState":
        specs = [
            self.seconds is not None,
            self.timestamp is not None,
            self.seconds_path is not None,
            self.timestamp_path is not None,
        ]
        count = sum(specs)
        if count != 1:
            raise ValueError("Wait state must specify exactly one of: Seconds, Timestamp, SecondsPath, TimestampPath")
        return self


class SucceedState(BaseModel):
    """Succeed state — terminal success."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    type: Literal["Succeed"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")

    input_path: str | None = Field(default=None, alias="InputPath")
    output_path: str | None = Field(default=None, alias="OutputPath")
    assign: dict[str, Any] | None = Field(default=None, alias="Assign")
    output: Any | None = Field(default=None, alias="Output")
    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")


class FailState(BaseModel):
    """Fail state — terminal failure.

    Inherits from BaseModel directly (NOT _IOFields) because ASL spec says
    Fail states do not process I/O.
    """

    model_config = {"extra": "forbid", "populate_by_name": True}

    type: Literal["Fail"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")

    error: str | None = Field(default=None, alias="Error")
    error_path: str | None = Field(default=None, alias="ErrorPath")
    cause: str | None = Field(default=None, alias="Cause")
    cause_path: str | None = Field(default=None, alias="CausePath")

    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")

    @model_validator(mode="after")
    def error_cause_mutual_exclusion(self) -> "FailState":
        if self.error is not None and self.error_path is not None:
            raise ValueError("Cannot specify both Error and ErrorPath")
        if self.cause is not None and self.cause_path is not None:
            raise ValueError("Cannot specify both Cause and CausePath")
        return self


class ProcessorConfig(BaseModel):
    """Configuration for Map state ItemProcessor."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    mode: ProcessorMode = Field(default=ProcessorMode.INLINE, alias="Mode")


class BranchDefinition(BaseModel):
    """A sub-state machine used in Parallel branches and Map ItemProcessor.

    States are initially parsed as dicts, then validated against the State
    union type in a model_validator that is injected by dsl/__init__.py.
    """

    model_config = {"extra": "forbid", "populate_by_name": True}

    start_at: str = Field(alias="StartAt")
    states: dict[str, Any] = Field(alias="States")
    comment: str | None = Field(default=None, alias="Comment")
    processor_config: ProcessorConfig | None = Field(default=None, alias="ProcessorConfig")
    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")

    @model_validator(mode="after")
    def _resolve_states(self) -> "BranchDefinition":
        if _state_validator is not None:
            self.states = _state_validator(self.states)
        return self


class ParallelState(_IOFields, _TransitionFields, _AssignOutput):
    """Parallel state — concurrent execution of branches."""

    type: Literal["Parallel"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")
    branches: list[BranchDefinition] = Field(alias="Branches")

    retry: list[RetryPolicy] | None = Field(default=None, alias="Retry")
    catch: list[Catcher] | None = Field(default=None, alias="Catch")

    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")


class MapState(_IOFields, _TransitionFields, _AssignOutput):
    """Map state — iterates over an array with a sub-state machine."""

    type: Literal["Map"] = Field(alias="Type")
    comment: str | None = Field(default=None, alias="Comment")

    item_processor: BranchDefinition | None = Field(default=None, alias="ItemProcessor")
    items_path: str | None = Field(default=None, alias="ItemsPath")
    max_concurrency: int | None = Field(default=None, alias="MaxConcurrency", ge=0)
    item_selector: dict[str, Any] | None = Field(default=None, alias="ItemSelector")

    retry: list[RetryPolicy] | None = Field(default=None, alias="Retry")
    catch: list[Catcher] | None = Field(default=None, alias="Catch")

    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")


# Hook for state validation — set by dsl/__init__.py after the State type is assembled
_state_validator: Any = None


# Placeholder for the discriminated union — assembled in dsl/__init__.py
State = Any


class StateMachineDefinition(BaseModel):
    """Root model for an RSF workflow definition."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    rsf_version: str = Field(default="1.0", alias="rsf_version")
    comment: str | None = Field(default=None, alias="Comment")
    start_at: str = Field(alias="StartAt")
    states: dict[str, Any] = Field(alias="States")
    version: str | None = Field(default=None, alias="Version")
    timeout_seconds: int | None = Field(default=None, alias="TimeoutSeconds", ge=0)
    query_language: QueryLanguage | None = Field(default=None, alias="QueryLanguage")

    @model_validator(mode="after")
    def _resolve_states(self) -> "StateMachineDefinition":
        if _state_validator is not None:
            self.states = _state_validator(self.states)
        return self
