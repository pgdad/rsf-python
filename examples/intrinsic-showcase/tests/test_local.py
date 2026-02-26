"""Local tests for the intrinsic-showcase example.

Verifies:
 1. workflow.yaml parses via rsf.dsl.parser.load_definition
 2. 14+ unique intrinsic functions are referenced in the YAML
 3. All 5 I/O pipeline fields are present in the YAML
 4. Each handler works in isolation
 5. Workflow simulation with MockDurableContext
"""

import re
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


# ---------------------------------------------------------------------------
# 2. Intrinsic function coverage (14+ unique functions)
# ---------------------------------------------------------------------------

# All 17 intrinsic functions supported by the RSF project
ALL_INTRINSIC_FUNCTIONS = [
    "States.Format",
    "States.StringSplit",
    "States.Array",
    "States.ArrayPartition",
    "States.ArrayContains",
    "States.ArrayRange",
    "States.ArrayGetItem",
    "States.ArrayLength",
    "States.ArrayUnique",
    "States.MathRandom",
    "States.MathAdd",
    "States.StringToJson",
    "States.JsonToString",
    "States.Base64Encode",
    "States.Base64Decode",
    "States.Hash",
    "States.UUID",
]


class TestIntrinsicCoverage:
    def test_at_least_14_intrinsic_functions(self):
        """workflow.yaml must reference at least 14 unique intrinsic functions."""
        yaml_text = WORKFLOW_YAML.read_text(encoding="utf-8")
        found = set()
        for func_name in ALL_INTRINSIC_FUNCTIONS:
            # Use word-boundary-safe matching: func_name followed by '('
            pattern = re.escape(func_name) + r"\s*\("
            if re.search(pattern, yaml_text):
                found.add(func_name)
        assert len(found) >= 14, (
            f"Expected 14+ intrinsic functions, found {len(found)}: {sorted(found)}"
        )

    def test_specific_functions_present(self):
        """Verify key intrinsic functions are used."""
        yaml_text = WORKFLOW_YAML.read_text(encoding="utf-8")
        must_have = [
            "States.Format",
            "States.UUID",
            "States.Base64Encode",
            "States.Base64Decode",
            "States.Hash",
            "States.MathAdd",
            "States.ArrayContains",
            "States.ArrayRange",
        ]
        for func_name in must_have:
            assert func_name in yaml_text, f"Missing intrinsic function: {func_name}"


# ---------------------------------------------------------------------------
# 3. All 5 I/O pipeline fields present
# ---------------------------------------------------------------------------


class TestIOPipelineFields:
    def test_all_five_io_fields_present(self):
        """workflow.yaml must use all 5 I/O pipeline fields at least once."""
        yaml_text = WORKFLOW_YAML.read_text(encoding="utf-8")
        io_fields = ["InputPath", "Parameters", "ResultSelector", "ResultPath", "OutputPath"]
        for field_name in io_fields:
            # Match field at start of a YAML key (with optional indentation)
            assert field_name in yaml_text, (
                f"I/O pipeline field '{field_name}' not found in workflow.yaml"
            )


# ---------------------------------------------------------------------------
# 4. Individual handler tests
# ---------------------------------------------------------------------------


class TestStringOperationsHandler:
    def test_returns_all_fields(self):
        """StringOperations handler returns decoded, hash, serialized, formatted."""
        from handlers.string_operations import string_operations

        event = {
            "decoded": "Jane Doe",
            "hash": "abc123def456",
            "serialized": '["Jane", "Doe"]',
            "formatted": "Jane Doe has 2 name parts",
        }
        result = string_operations(event)
        assert result["decoded"] == "Jane Doe"
        assert result["hash"] == "abc123def456"
        assert result["serialized"] == '["Jane", "Doe"]'
        assert result["formatted"] == "Jane Doe has 2 name parts"

    def test_handles_missing_fields(self):
        """StringOperations handler defaults gracefully for missing keys."""
        from handlers.string_operations import string_operations

        result = string_operations({})
        assert result["decoded"] == ""
        assert result["hash"] == ""
        assert result["serialized"] == ""
        assert result["formatted"] == ""


class TestArrayOperationsHandler:
    def test_returns_all_fields(self):
        """ArrayOperations handler returns range, partitioned, contains, etc."""
        from handlers.array_operations import array_operations

        event = {
            "range": [1, 3, 5, 7, 9],
            "partitioned": [["demo", "showcase"], ["intrinsics"]],
            "contains": True,
            "firstTag": "demo",
            "tagCount": 3,
            "uniqueTags": ["a", "b", "c"],
        }
        result = array_operations(event)
        assert result["range"] == [1, 3, 5, 7, 9]
        assert result["partitioned"] == [["demo", "showcase"], ["intrinsics"]]
        assert result["contains"] is True
        assert result["firstTag"] == "demo"
        assert result["tagCount"] == 3
        assert result["uniqueTags"] == ["a", "b", "c"]

    def test_handles_missing_fields(self):
        """ArrayOperations handler defaults gracefully for missing keys."""
        from handlers.array_operations import array_operations

        result = array_operations({})
        assert result["range"] == []
        assert result["partitioned"] == []
        assert result["contains"] is False
        assert result["firstTag"] == ""
        assert result["tagCount"] == 0
        assert result["uniqueTags"] == []


class TestMathAndJsonOpsHandler:
    def test_returns_all_fields(self):
        """MathAndJsonOps handler returns sum, randomVal, parsed."""
        from handlers.math_and_json_ops import math_and_json_ops

        event = {
            "sum": 13,
            "randomVal": 42,
            "parsed": ["Jane", "Doe"],
        }
        result = math_and_json_ops(event)
        assert result["sum"] == 13
        assert result["randomVal"] == 42
        assert result["parsed"] == ["Jane", "Doe"]

    def test_handles_missing_fields(self):
        """MathAndJsonOps handler defaults gracefully for missing keys."""
        from handlers.math_and_json_ops import math_and_json_ops

        result = math_and_json_ops({})
        assert result["sum"] == 0
        assert result["randomVal"] == 0
        assert result["parsed"] is None


# ---------------------------------------------------------------------------
# 5. Workflow simulation with MockDurableContext
# ---------------------------------------------------------------------------


class TestWorkflowSimulation:
    def test_full_workflow_with_mock_context(self):
        """Simulate the full workflow using MockDurableContext.

        Pre-configures step overrides that mimic intrinsic-function evaluation
        results for each Task state, then drives the workflow through all states.
        """
        from mock_sdk import MockDurableContext
        from rsf.registry import discover_handlers, get_handler

        discover_handlers(EXAMPLE_ROOT / "handlers")

        ctx = MockDurableContext()

        # --- PrepareData (Pass state) - simulated inline ---
        workflow_input = {
            "input": {"userName": "Jane Doe"},
        }

        # Simulate PrepareData (Pass state -- no handler, just I/O pipeline)
        prepared_data = {
            "greeting": "Welcome, Jane Doe!",
            "requestId": "550e8400-e29b-41d4-a716-446655440000",
            "nameParts": ["Jane", "Doe"],
            "tagArray": ["demo", "showcase", "intrinsics"],
            "encoded": "SmFuZSBEb2U=",
        }
        state_data = {**workflow_input, "prepared": prepared_data}

        # --- StringOperations (Task state) ---
        string_input = {
            "decoded": "Jane Doe",
            "hash": "a1b2c3d4e5f6",
            "serialized": '["Jane","Doe"]',
            "formatted": "Jane Doe has 2 name parts",
        }
        string_handler = get_handler("StringOperations")
        string_result = ctx.step("StringOperations", string_handler, string_input)

        assert string_result["decoded"] == "Jane Doe"
        assert string_result["hash"] == "a1b2c3d4e5f6"

        # Apply ResultSelector + ResultPath
        state_data["strings"] = {"stringResults": string_result}

        # --- ArrayOperations (Task state) ---
        array_input = {
            "range": [1, 3, 5, 7, 9],
            "partitioned": [["demo", "showcase"], ["intrinsics"]],
            "contains": True,
            "firstTag": "demo",
            "tagCount": 3,
            "uniqueTags": ["a", "b", "c"],
        }
        array_handler = get_handler("ArrayOperations")
        array_result = ctx.step("ArrayOperations", array_handler, array_input)

        assert array_result["contains"] is True
        assert array_result["tagCount"] == 3

        # Apply ResultSelector + ResultPath
        state_data["arrays"] = {"arrayResults": array_result}

        # --- MathAndJsonOps (Task state) ---
        math_input = {
            "sum": 13,
            "randomVal": 42,
            "parsed": ["Jane", "Doe"],
        }
        math_handler = get_handler("MathAndJsonOps")
        math_result = ctx.step("MathAndJsonOps", math_handler, math_input)

        assert math_result["sum"] == 13
        assert math_result["parsed"] == ["Jane", "Doe"]

        # Apply ResultPath
        state_data["math"] = math_result

        # --- CheckResults (Choice state) -- simulated ---
        assert state_data["arrays"]["arrayResults"]["contains"] is True
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

        # Override all handlers with canned results
        ctx.override_step("StringOperations", {
            "decoded": "Test User",
            "hash": "deadbeef",
            "serialized": '["Test","User"]',
            "formatted": "Test User has 2 name parts",
        })
        ctx.override_step("ArrayOperations", {
            "range": [1, 3, 5],
            "partitioned": [["a", "b"]],
            "contains": True,
            "firstTag": "a",
            "tagCount": 2,
            "uniqueTags": ["a", "b"],
        })
        ctx.override_step("MathAndJsonOps", {
            "sum": 12,
            "randomVal": 77,
            "parsed": ["Test", "User"],
        })

        # Execute steps using overrides
        string_handler = get_handler("StringOperations")
        result1 = ctx.step("StringOperations", string_handler, {})
        assert result1["decoded"] == "Test User"

        array_handler = get_handler("ArrayOperations")
        result2 = ctx.step("ArrayOperations", array_handler, {})
        assert result2["contains"] is True

        math_handler = get_handler("MathAndJsonOps")
        result3 = ctx.step("MathAndJsonOps", math_handler, {})
        assert result3["sum"] == 12

        assert len(ctx.calls) == 3
