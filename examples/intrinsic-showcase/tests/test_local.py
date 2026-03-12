"""Local tests for the intrinsic-showcase example.

Verifies:
 1. workflow.yaml parses via rsf.dsl.parser.load_definition
 2. All 6 states are present
 3. Each handler computes expected outputs from prepared data
 4. Workflow simulation with MockDurableContext
"""

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

EXAMPLE_ROOT = Path(__file__).parent.parent
WORKFLOW_YAML = EXAMPLE_ROOT / "workflow.yaml"

# ---------------------------------------------------------------------------
# 1. Workflow YAML parses correctly
# ---------------------------------------------------------------------------


class TestWorkflowParsing:
    def test_load_definition(self):
        """workflow.yaml must parse into a valid StateMachineDefinition."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.start_at == "PrepareData"
        assert "PrepareData" in definition.states
        assert "StringOperations" in definition.states
        assert "ArrayOperations" in definition.states
        assert "MathAndJsonOps" in definition.states
        assert "CheckResults" in definition.states
        assert "ShowcaseComplete" in definition.states

    def test_state_count(self):
        """Workflow should contain exactly 6 states."""
        definition = load_definition(WORKFLOW_YAML)
        assert len(definition.states) == 6

    def test_prepare_data_result_path(self):
        """PrepareData should set $.prepared."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.states["PrepareData"].result_path == "$.prepared"

    def test_string_operations_result_path(self):
        """StringOperations should set $.strings."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.states["StringOperations"].result_path == "$.strings"

    def test_array_operations_result_path(self):
        """ArrayOperations should set $.arrays."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.states["ArrayOperations"].result_path == "$.arrays"

    def test_math_ops_result_path(self):
        """MathAndJsonOps should set $.math."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.states["MathAndJsonOps"].result_path == "$.math"

    def test_check_results_default(self):
        """CheckResults default should route to ShowcaseComplete."""
        definition = load_definition(WORKFLOW_YAML)
        assert definition.states["CheckResults"].default == "ShowcaseComplete"


# ---------------------------------------------------------------------------
# 2. Individual handler tests
# ---------------------------------------------------------------------------


class TestStringOperationsHandler:
    def test_returns_all_fields(self):
        """StringOperations handler returns decoded, hash, serialized, formatted."""
        from handlers.string_operations import string_operations

        event = {
            "prepared": {
                "userName": "Jane Doe",
                "tagArray": ["demo", "showcase", "intrinsics"],
            }
        }
        result = string_operations(event)
        assert result["decoded"] == "Jane Doe"
        assert len(result["hash"]) > 0
        assert "Jane" in result["serialized"]
        assert "Jane Doe" in result["formatted"]

    def test_handles_missing_prepared(self):
        """StringOperations handler defaults gracefully for missing prepared key."""
        from handlers.string_operations import string_operations

        result = string_operations({})
        assert result["decoded"] == ""
        # hash of empty greeting "Welcome, !" is deterministic
        assert len(result["hash"]) > 0
        assert result["serialized"] == "[]"
        assert result["formatted"] == " has 0 name parts"


class TestArrayOperationsHandler:
    def test_returns_all_fields(self):
        """ArrayOperations handler returns range, partitioned, contains, etc."""
        from handlers.array_operations import array_operations

        event = {
            "prepared": {
                "tagArray": ["demo", "showcase", "intrinsics"],
            }
        }
        result = array_operations(event)
        assert result["range"] == [1, 3, 5, 7, 9]
        assert result["contains"] is True
        assert result["firstTag"] == "demo"
        assert result["tagCount"] == 3
        assert isinstance(result["uniqueTags"], list)
        assert isinstance(result["partitioned"], list)

    def test_handles_missing_prepared(self):
        """ArrayOperations handler defaults gracefully for missing prepared key."""
        from handlers.array_operations import array_operations

        result = array_operations({})
        assert result["range"] == [1, 3, 5, 7, 9]
        assert result["partitioned"] == []
        assert result["contains"] is False
        assert result["firstTag"] == ""
        assert result["tagCount"] == 0


class TestMathAndJsonOpsHandler:
    def test_returns_all_fields(self):
        """MathAndJsonOps handler returns sum, randomVal, parsed."""
        from handlers.math_and_json_ops import math_and_json_ops

        event = {
            "arrays": {"tagCount": 3},
            "strings": {"serialized": '["Jane", "Doe"]'},
        }
        result = math_and_json_ops(event)
        assert result["sum"] == 13  # 3 + 10
        assert 1 <= result["randomVal"] <= 100
        assert result["parsed"] == ["Jane", "Doe"]

    def test_handles_missing_arrays(self):
        """MathAndJsonOps handler defaults gracefully for missing arrays key."""
        from handlers.math_and_json_ops import math_and_json_ops

        result = math_and_json_ops({})
        assert result["sum"] == 10  # 0 + 10
        assert 1 <= result["randomVal"] <= 100
        # json.loads("[]") returns [] (not None) as the default "[]" string is valid JSON
        assert isinstance(result["parsed"], list)


# ---------------------------------------------------------------------------
# 3. Workflow simulation with MockDurableContext
# ---------------------------------------------------------------------------


class TestWorkflowSimulation:
    def test_full_workflow_with_mock_context(self):
        """Simulate the full workflow using MockDurableContext."""
        from mock_sdk import MockDurableContext
        from rsf.registry import discover_handlers, get_handler

        discover_handlers(EXAMPLE_ROOT / "handlers")

        ctx = MockDurableContext()

        workflow_input = {"input": {"userName": "Jane Doe"}}

        # --- PrepareData (Pass state) - sets $.prepared inline ---
        prepared = {"userName": "Jane Doe", "tagArray": ["demo", "showcase", "intrinsics"]}
        state_data = {**workflow_input, "prepared": prepared}

        # --- StringOperations (Task state) ---
        string_handler = get_handler("StringOperations")
        string_result = ctx.step(lambda _sc: string_handler(state_data), "StringOperations")

        assert string_result["decoded"] == "Jane Doe"
        assert len(string_result["hash"]) > 0

        state_data["strings"] = string_result

        # --- ArrayOperations (Task state) ---
        array_handler = get_handler("ArrayOperations")
        array_result = ctx.step(lambda _sc: array_handler(state_data), "ArrayOperations")

        assert array_result["contains"] is True
        assert array_result["tagCount"] == 3

        state_data["arrays"] = array_result

        # --- MathAndJsonOps (Task state) ---
        math_handler = get_handler("MathAndJsonOps")
        math_result = ctx.step(lambda _sc: math_handler(state_data), "MathAndJsonOps")

        assert math_result["sum"] == 13  # tagCount(3) + 10
        assert isinstance(math_result["parsed"], list)

        state_data["math"] = math_result

        # --- CheckResults (Choice state) -- simulated ---
        assert state_data["arrays"]["contains"] is True
        # Choice routes to ShowcaseComplete

        # --- Verify MockDurableContext recorded all 3 Task steps ---
        assert len(ctx.calls) == 3
        step_names = [c.name for c in ctx.calls]
        assert step_names == ["StringOperations", "ArrayOperations", "MathAndJsonOps"]

    def test_step_overrides(self):
        """Verify workflow works with pre-configured step overrides."""
        from mock_sdk import MockDurableContext
        from rsf.registry import discover_handlers, get_handler

        discover_handlers(EXAMPLE_ROOT / "handlers")

        ctx = MockDurableContext()

        ctx.override_step(
            "StringOperations",
            {
                "decoded": "Test User",
                "hash": "deadbeef",
                "serialized": '["Test","User"]',
                "formatted": "Test User has 2 name parts",
            },
        )
        ctx.override_step(
            "ArrayOperations",
            {
                "range": [1, 3, 5],
                "partitioned": [["a", "b"]],
                "contains": True,
                "firstTag": "a",
                "tagCount": 2,
                "uniqueTags": ["a", "b"],
            },
        )
        ctx.override_step(
            "MathAndJsonOps",
            {
                "sum": 12,
                "randomVal": 77,
                "parsed": ["Test", "User"],
            },
        )

        string_handler = get_handler("StringOperations")
        result1 = ctx.step(lambda _sc: string_handler({}), "StringOperations")
        assert result1["decoded"] == "Test User"

        array_handler = get_handler("ArrayOperations")
        result2 = ctx.step(lambda _sc: array_handler({}), "ArrayOperations")
        assert result2["contains"] is True

        math_handler = get_handler("MathAndJsonOps")
        result3 = ctx.step(lambda _sc: math_handler({}), "MathAndJsonOps")
        assert result3["sum"] == 12

        assert len(ctx.calls) == 3
