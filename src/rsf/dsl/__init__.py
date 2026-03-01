"""DSL package — assembles the State discriminated union and resolves forward refs.

This module breaks the circular import between ChoiceState (references State via
boolean combinators) and State (references ChoiceState via discriminated union)
by doing late binding after all models are imported.
"""

from typing import Annotated, Any, Union

from pydantic import Field, TypeAdapter

from rsf.dsl.choice import (
    BooleanAndRule,
    BooleanNotRule,
    BooleanOrRule,
    ChoiceRule,
    ConditionRule,
    DataTestRule,
    discriminate_choice_rule,
)
from rsf.dsl.errors import Catcher, RetryPolicy
from rsf.dsl.models import (
    BranchDefinition,
    ChoiceState,
    FailState,
    LambdaUrlConfig,
    MapState,
    ParallelState,
    PassState,
    ProcessorConfig,
    StateMachineDefinition,
    SucceedState,
    TaskState,
    WaitState,
)
from rsf.dsl.types import (
    COMPARISON_OPERATORS,
    JitterStrategy,
    LambdaUrlAuthType,
    ProcessorMode,
    QueryLanguage,
)

# Assemble the discriminated State union
State = Annotated[
    Union[
        TaskState,
        PassState,
        ChoiceState,
        WaitState,
        SucceedState,
        FailState,
        ParallelState,
        MapState,
    ],
    Field(discriminator="type"),
]

# Create a TypeAdapter for validating individual state values
_state_adapter = TypeAdapter(State)


def _validate_states_dict(states: dict[str, Any]) -> dict[str, Any]:
    """Validate and parse a states dict, converting each value to a typed State."""
    result = {}
    for name, data in states.items():
        if isinstance(data, dict):
            result[name] = _state_adapter.validate_python(data)
        else:
            result[name] = data
    return result


# Inject the validator hook into models so it runs during normal Pydantic parsing
import rsf.dsl.models as _models  # noqa: E402

_models._state_validator = _validate_states_dict

__all__ = [
    "BooleanAndRule",
    "BooleanNotRule",
    "BooleanOrRule",
    "BranchDefinition",
    "Catcher",
    "ChoiceRule",
    "ChoiceState",
    "COMPARISON_OPERATORS",
    "ConditionRule",
    "DataTestRule",
    "FailState",
    "JitterStrategy",
    "LambdaUrlAuthType",
    "LambdaUrlConfig",
    "MapState",
    "ParallelState",
    "PassState",
    "ProcessorConfig",
    "ProcessorMode",
    "QueryLanguage",
    "RetryPolicy",
    "State",
    "StateMachineDefinition",
    "SucceedState",
    "TaskState",
    "WaitState",
    "discriminate_choice_rule",
]
