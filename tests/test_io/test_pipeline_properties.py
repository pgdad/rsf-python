"""Property-based tests for the 5-stage I/O processing pipeline.

Uses Hypothesis to verify pipeline invariants across randomly generated
inputs and JSONPath expressions. Complements handwritten unit tests
in test_pipeline.py.
"""

from __future__ import annotations

import copy

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from rsf.io.pipeline import process_jsonpath_pipeline


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------

# Leaf values that JSONPath can navigate
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.text(min_size=0, max_size=20),
)

# Valid field names for JSONPath dot notation
field_names = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,9}", fullmatch=True)

# Recursive JSON-like data structures
json_values = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(field_names, children, max_size=5),
    ),
    max_leaves=20,
)

# Dict-only structures (needed as raw_input for pipeline)
json_dicts = st.dictionaries(field_names, json_values, min_size=1, max_size=8)


@st.composite
def workflow_data(draw):
    """Generate realistic workflow-like data with typical keys."""
    base = {
        "order": {
            "id": draw(st.integers(min_value=1, max_value=99999)),
            "items": draw(
                st.lists(
                    st.dictionaries(
                        st.just("name"),
                        st.text(min_size=1, max_size=10),
                    ),
                    min_size=1,
                    max_size=5,
                )
            ),
            "status": draw(
                st.sampled_from(["pending", "approved", "rejected", "processing"])
            ),
        },
    }
    # Add random extra keys
    extras = draw(st.dictionaries(field_names, json_values, max_size=3))
    base.update(extras)
    return base


@st.composite
def jsonpath_expressions(draw):
    """Generate valid JSONPath expressions for property testing.

    Generates: $.field, $.a.b, $.arr[0], $['key']
    """
    style = draw(st.sampled_from(["dot", "dot_nested", "bracket", "array"]))
    if style == "dot":
        field = draw(field_names)
        return f"$.{field}"
    elif style == "dot_nested":
        parts = draw(st.lists(field_names, min_size=2, max_size=4))
        return "$." + ".".join(parts)
    elif style == "bracket":
        field = draw(field_names)
        return f"$['{field}']"
    else:  # array
        field = draw(field_names)
        idx = draw(st.integers(min_value=0, max_value=4))
        return f"$.{field}[{idx}]"


# ---------------------------------------------------------------------------
# Strategy Self-Tests
# ---------------------------------------------------------------------------


class TestStrategies:
    """Verify custom strategies produce valid output."""

    @given(path=jsonpath_expressions())
    @settings(max_examples=50)
    def test_jsonpath_starts_with_dollar(self, path):
        assert path.startswith("$")

    @given(path=jsonpath_expressions())
    @settings(max_examples=50)
    def test_jsonpath_has_field_reference(self, path):
        # All generated paths reference at least one field
        assert len(path) > 1

    @given(data=workflow_data())
    @settings(max_examples=50)
    def test_workflow_data_has_order(self, data):
        assert "order" in data
        assert "id" in data["order"]
        assert "items" in data["order"]
        assert "status" in data["order"]


# ---------------------------------------------------------------------------
# Property: ResultPath merges into RAW input, not effective input
# ---------------------------------------------------------------------------


class TestResultPathMergesIntoRaw:
    """Property: ResultPath merges result into RAW input, not effective input."""

    @given(
        raw=json_dicts,
        task_result=json_values,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_result_path_merges_into_raw(self, raw, task_result):
        """After InputPath filters to a subset, ResultPath still merges
        into the full raw_input, preserving all original keys."""
        if not raw:
            return  # skip empty dicts

        # Pick a key that exists for InputPath
        key = next(iter(raw))
        result_key = "_test_result"

        output = process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            input_path=f"$.{key}",
            result_path=f"$.{result_key}",
        )

        # All original keys from raw must be present (ResultPath merges into raw)
        for k in raw:
            assert k in output, (
                f"Key '{k}' from raw_input missing in output. "
                f"ResultPath may have merged into effective input instead of raw."
            )
        # The result must be at the specified path
        assert result_key in output


# ---------------------------------------------------------------------------
# Property: Pipeline never mutates raw_input or task_result in-place
# ---------------------------------------------------------------------------


class TestPipelineNeverMutatesInputs:
    """Property: Pipeline never mutates raw_input or task_result in-place."""

    @given(
        raw=json_dicts,
        task_result=json_values,
        result_path=st.sampled_from(["$", "$.out", None]),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_pipeline_never_mutates_inputs(self, raw, task_result, result_path):
        raw_before = copy.deepcopy(raw)
        result_before = copy.deepcopy(task_result)

        process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            result_path=result_path,
        )

        assert raw == raw_before, "raw_input was mutated in-place"
        assert task_result == result_before, "task_result was mutated in-place"


# ---------------------------------------------------------------------------
# Property: OutputPath output is valid subset of merged result
# ---------------------------------------------------------------------------


class TestOutputPathIsSubset:
    """Property: OutputPath output is always a valid subset of the merged result."""

    @given(
        raw=json_dicts,
        task_result=json_dicts,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_output_path_selects_subset(self, raw, task_result):
        """OutputPath $.key returns exactly the value at that key
        from the merged result."""
        # Get the merged result (result_path="$" -> merged = task_result)
        merged = process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            result_path="$",
        )

        if not isinstance(merged, dict) or not merged:
            return  # skip non-dict or empty merged results

        # Pick a key from the merged result
        key = next(iter(merged))

        output = process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            result_path="$",
            output_path=f"$.{key}",
        )

        assert output == merged[key]


# ---------------------------------------------------------------------------
# Property: ResultPath special cases (null discards, $ replaces)
# ---------------------------------------------------------------------------


class TestResultPathSpecialCases:
    """Property: ResultPath null and $ have correct semantics."""

    @given(
        raw=json_dicts,
        task_result=json_values,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_result_path_null_discards(self, raw, task_result):
        """When result_path=None, output equals raw_input (result discarded)."""
        output = process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            result_path=None,
        )
        assert output == raw

    @given(
        raw=json_dicts,
        task_result=json_values,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_result_path_dollar_replaces(self, raw, task_result):
        """When result_path='$', output equals task_result (replaces entirely)."""
        output = process_jsonpath_pipeline(
            raw_input=raw,
            task_result=task_result,
            result_path="$",
        )
        assert output == task_result


# ---------------------------------------------------------------------------
# Property: Workflow data survives full pipeline
# ---------------------------------------------------------------------------


class TestWorkflowDataSurvivesPipeline:
    """Property: Realistic workflow data passes through pipeline without errors."""

    @given(data=workflow_data())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_workflow_data_full_pipeline(self, data):
        """Full pipeline with realistic data should not raise."""
        output = process_jsonpath_pipeline(
            raw_input=data,
            task_result={"processed": True, "count": 42},
            input_path="$.order",
            result_path="$.taskResult",
            output_path="$.taskResult",
        )
        assert output == {"processed": True, "count": 42}
