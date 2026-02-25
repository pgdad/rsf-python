"""Tests for the 5-stage I/O processing pipeline."""

import pytest

from rsf.io.jsonpath import JSONPathError, evaluate_jsonpath
from rsf.io.payload_template import apply_payload_template
from rsf.io.result_path import apply_result_path
from rsf.io.pipeline import process_jsonpath_pipeline
from rsf.variables.store import VariableStore


class TestJSONPath:
    def test_root(self):
        assert evaluate_jsonpath({"a": 1}, "$") == {"a": 1}

    def test_dot_notation(self):
        assert evaluate_jsonpath({"a": {"b": 42}}, "$.a.b") == 42

    def test_bracket_notation(self):
        assert evaluate_jsonpath({"key name": "val"}, "$['key name']") == "val"

    def test_array_index(self):
        assert evaluate_jsonpath({"arr": [10, 20, 30]}, "$.arr[0]") == 10
        assert evaluate_jsonpath({"arr": [10, 20, 30]}, "$.arr[2]") == 30

    def test_nested_path(self):
        data = {"a": {"b": [{"c": 99}]}}
        assert evaluate_jsonpath(data, "$.a.b[0].c") == 99

    def test_missing_key_raises(self):
        with pytest.raises(JSONPathError, match="not found"):
            evaluate_jsonpath({"a": 1}, "$.b")

    def test_array_out_of_range(self):
        with pytest.raises(JSONPathError, match="out of range"):
            evaluate_jsonpath({"arr": [1]}, "$.arr[5]")

    def test_context_reference(self):
        class FakeCtx:
            class Execution:
                Id = "exec-123"
        assert evaluate_jsonpath(None, "$$.Execution.Id", context=FakeCtx()) == "exec-123"

    def test_variable_reference(self):
        store = VariableStore()
        store.set("count", 42)
        assert evaluate_jsonpath(None, "$count", variables=store) == 42

    def test_none_path_returns_data(self):
        assert evaluate_jsonpath({"x": 1}, None) == {"x": 1}


class TestPayloadTemplate:
    def test_static_keys(self):
        result = apply_payload_template(
            {"key": "value", "num": 42},
            {"ignored": True},
        )
        assert result == {"key": "value", "num": 42}

    def test_dynamic_keys(self):
        result = apply_payload_template(
            {"name.$": "$.name", "static": "yes"},
            {"name": "Alice"},
        )
        assert result == {"name": "Alice", "static": "yes"}

    def test_nested_templates(self):
        result = apply_payload_template(
            {"outer": {"inner.$": "$.val"}},
            {"val": 99},
        )
        assert result == {"outer": {"inner": 99}}


class TestResultPath:
    def test_replace_all(self):
        assert apply_result_path({"old": 1}, {"new": 2}, "$") == {"new": 2}

    def test_merge_at_path(self):
        result = apply_result_path(
            {"x": 1, "y": 2}, {"done": True}, "$.taskResult"
        )
        assert result == {"x": 1, "y": 2, "taskResult": {"done": True}}

    def test_discard_result(self):
        result = apply_result_path({"x": 1}, {"ignored": True}, None)
        assert result == {"x": 1}

    def test_deep_copy(self):
        raw = {"x": [1, 2]}
        result_data = {"y": 3}
        output = apply_result_path(raw, result_data, "$.out")
        output["x"].append(99)
        assert raw["x"] == [1, 2]  # Not mutated

    def test_nested_result_path(self):
        result = apply_result_path({}, "val", "$.a.b.c")
        assert result == {"a": {"b": {"c": "val"}}}


class TestPipeline:
    def test_full_pipeline(self):
        output = process_jsonpath_pipeline(
            raw_input={"order": {"id": 123, "items": [1, 2]}, "meta": "keep"},
            task_result={"processed": True, "count": 3},
            input_path="$.order",
            parameters={"orderId.$": "$.id"},
            result_selector={"done.$": "$.processed"},
            result_path="$.taskResult",
            output_path="$.taskResult",
        )
        assert output == {"done": True}

    def test_pipeline_no_transforms(self):
        output = process_jsonpath_pipeline(
            raw_input={"data": 42},
            task_result={"result": "ok"},
        )
        assert output == {"result": "ok"}

    def test_pipeline_result_merges_into_raw_input(self):
        """Critical: ResultPath merges into RAW input, not effective input."""
        output = process_jsonpath_pipeline(
            raw_input={"a": 1, "b": 2},
            task_result={"c": 3},
            input_path="$.a",
            result_path="$.result",
        )
        # InputPath filters to just 1, but ResultPath merges into raw: {a:1, b:2}
        assert output == {"a": 1, "b": 2, "result": {"c": 3}}

    def test_pipeline_input_path_only(self):
        output = process_jsonpath_pipeline(
            raw_input={"nested": {"val": 42}},
            task_result="ignored",
            input_path="$.nested",
            result_path=None,
        )
        assert output == {"nested": {"val": 42}}
