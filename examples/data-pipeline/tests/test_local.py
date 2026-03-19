"""Local tests for the data-pipeline example.

Tests cover:
1. Workflow YAML parsing via rsf.dsl.parser.load_definition
2. Individual handler unit tests
3. Full pipeline simulation using MockDurableContext
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition
from rsf.dsl import (
    MapState,
    PassState,
    TaskState,
)
from mock_sdk import MockDurableContext


WORKFLOW_PATH = Path(__file__).parent.parent / "workflow.yaml"


# ---------------------------------------------------------------------------
# 1. Workflow YAML parsing
# ---------------------------------------------------------------------------


class TestWorkflowParsing:
    """Verify the workflow.yaml file parses correctly."""

    def test_load_definition_succeeds(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.start_at == "InitPipeline"

    def test_all_states_present(self):
        sm = load_definition(WORKFLOW_PATH)
        expected = {"InitPipeline", "FetchRecords", "TransformRecords", "StoreResults", "PipelineComplete"}
        assert set(sm.states.keys()) == expected

    def test_state_types(self):
        sm = load_definition(WORKFLOW_PATH)
        assert isinstance(sm.states["InitPipeline"], PassState)
        assert isinstance(sm.states["FetchRecords"], TaskState)
        assert isinstance(sm.states["TransformRecords"], MapState)
        assert isinstance(sm.states["StoreResults"], TaskState)
        assert isinstance(sm.states["PipelineComplete"], PassState)

    def test_state_transitions(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.states["InitPipeline"].next == "FetchRecords"
        assert sm.states["FetchRecords"].next == "TransformRecords"
        assert sm.states["TransformRecords"].next == "StoreResults"
        assert sm.states["StoreResults"].next == "PipelineComplete"
        assert sm.states["PipelineComplete"].end is True

    def test_map_state_structure(self):
        sm = load_definition(WORKFLOW_PATH)
        map_state = sm.states["TransformRecords"]
        assert map_state.items_path == "$.fetched.records"
        assert map_state.max_concurrency == 5
        assert map_state.item_processor is not None
        assert map_state.item_processor.start_at == "ValidateRecord"
        inner_states = map_state.item_processor.states
        assert "ValidateRecord" in inner_states
        assert "EnrichRecord" in inner_states

    def test_init_pipeline_has_result_path(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.states["InitPipeline"].result_path == "$.config"

    def test_fetch_records_has_result_path(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.states["FetchRecords"].result_path == "$.fetched"

    def test_transform_records_has_result_path(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.states["TransformRecords"].result_path == "$.transformed"

    def test_store_results_has_result_path(self):
        sm = load_definition(WORKFLOW_PATH)
        assert sm.states["StoreResults"].result_path == "$.stored"


# ---------------------------------------------------------------------------
# 2. Individual handler unit tests
# ---------------------------------------------------------------------------


class TestFetchRecordsHandler:
    """Unit tests for the FetchRecords handler."""

    def test_returns_records_and_count(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({"source": {"bucket": "my-bucket", "prefix": "data/"}})
        assert "records" in result
        assert "count" in result
        assert isinstance(result["records"], list)
        assert result["count"] == len(result["records"])

    def test_records_have_expected_structure(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({"source": {"bucket": "test-bucket", "prefix": "input/"}})
        for item in result["records"]:
            assert "id" in item
            assert "value" in item
            assert "source" in item
            assert item["source"].startswith("s3://test-bucket/input/")

    def test_default_values(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({})
        assert result["count"] > 0
        assert result["records"][0]["source"].startswith("s3://default-bucket/data/")


class TestValidateRecordHandler:
    """Unit tests for the ValidateRecord handler."""

    def test_valid_record_passes(self):
        from handlers.validate_record import validate_record

        record = {"id": "rec-1", "value": 42}
        result = validate_record(record)
        assert result["validated"] is True
        assert result["id"] == "rec-1"
        assert result["value"] == 42

    def test_preserves_extra_fields(self):
        from handlers.validate_record import validate_record

        record = {"id": "rec-1", "value": 10, "source": "s3://bucket/key"}
        result = validate_record(record)
        assert result["source"] == "s3://bucket/key"

    def test_missing_id_raises(self):
        from handlers.validate_record import validate_record

        with pytest.raises(ValueError, match="missing required fields"):
            validate_record({"value": 10})

    def test_missing_value_raises(self):
        from handlers.validate_record import validate_record

        with pytest.raises(ValueError, match="missing required fields"):
            validate_record({"id": "rec-1"})

    def test_empty_record_raises(self):
        from handlers.validate_record import validate_record

        with pytest.raises(ValueError, match="missing required fields"):
            validate_record({})


class TestEnrichRecordHandler:
    """Unit tests for the EnrichRecord handler."""

    def test_adds_enriched_at(self):
        from handlers.enrich_record import enrich_record

        record = {"id": "rec-1", "value": 42, "validated": True}
        result = enrich_record(record)
        assert "enrichedAt" in result
        assert "T" in result["enrichedAt"]

    def test_adds_hash(self):
        from handlers.enrich_record import enrich_record

        record = {"id": "rec-1", "value": 42, "validated": True}
        result = enrich_record(record)
        assert "hash" in result
        assert len(result["hash"]) == 16

    def test_preserves_original_fields(self):
        from handlers.enrich_record import enrich_record

        record = {"id": "rec-2", "value": 99, "validated": True, "source": "s3://b/k"}
        result = enrich_record(record)
        assert result["id"] == "rec-2"
        assert result["value"] == 99
        assert result["validated"] is True
        assert result["source"] == "s3://b/k"

    def test_deterministic_hash_for_same_input(self):
        from handlers.enrich_record import enrich_record

        record = {"id": "rec-1", "value": 42}
        r1 = enrich_record(record)
        r2 = enrich_record(record)
        assert r1["hash"] == r2["hash"]


class TestStoreResultsHandler:
    """Unit tests for the StoreResults handler."""

    def test_returns_items_written_count(self):
        from handlers.store_results import store_results

        items = [{"id": "rec-1"}, {"id": "rec-2"}, {"id": "rec-3"}]
        result = store_results(
            {
                "config": {"config": {"tableName": "my-table"}},
                "transformed": items,
            }
        )
        assert result["itemsWritten"] == 3
        assert result["tableName"] == "my-table"

    def test_empty_items(self):
        from handlers.store_results import store_results

        result = store_results(
            {
                "config": {"config": {"tableName": "t"}},
                "transformed": [],
            }
        )
        assert result["itemsWritten"] == 0

    def test_default_table_name(self):
        from handlers.store_results import store_results

        result = store_results({"transformed": [{"id": "1"}]})
        assert result["tableName"] == "unknown-table"
        assert result["itemsWritten"] == 1


# ---------------------------------------------------------------------------
# 3. Full pipeline simulation with MockDurableContext
# ---------------------------------------------------------------------------


class TestFullPipelineSimulation:
    """End-to-end pipeline simulation using MockDurableContext."""

    @pytest.fixture
    def pipeline_input(self):
        return {
            "source": {
                "bucket": "data-lake",
                "prefix": "incoming/2026-02-26/",
            }
        }

    @pytest.fixture
    def handlers(self):
        """Import and register all handlers, returning them by name."""
        from handlers.fetch_records import fetch_records
        from handlers.validate_record import validate_record
        from handlers.enrich_record import enrich_record
        from handlers.store_results import store_results

        return {
            "FetchRecords": fetch_records,
            "ValidateRecord": validate_record,
            "EnrichRecord": enrich_record,
            "StoreResults": store_results,
        }

    def test_full_pipeline_execution(self, pipeline_input, handlers):
        """Execute the full pipeline and verify the end-to-end result."""
        ctx = MockDurableContext()

        # Simulate the full orchestrator flow
        input_data = pipeline_input

        # InitPipeline (Pass): sets $.config
        input_data = {
            **input_data,
            "config": {
                "pipeline": "etl-v1",
                "stage": "initialized",
                "config": {"batchSize": 10, "tableName": "pipeline-results"},
            },
        }

        # FetchRecords: receives full input_data, returns {records, count}
        fetch_result = ctx.step(lambda _sc: handlers["FetchRecords"](input_data), "FetchRecords")
        assert "records" in fetch_result
        input_data = {**input_data, "fetched": fetch_result}

        # TransformRecords (Map): processes each record
        records = input_data["fetched"]["records"]

        def map_item_processor(_ctx, item, _idx, _all):
            validated = handlers["ValidateRecord"](item)
            enriched = handlers["EnrichRecord"](validated)
            return enriched

        map_result = ctx.map(records, map_item_processor, "TransformRecords")
        transformed = map_result.get_results()
        input_data = {**input_data, "transformed": transformed}

        # StoreResults: receives full input_data
        store_result = ctx.step(lambda _sc: handlers["StoreResults"](input_data), "StoreResults")
        input_data = {**input_data, "stored": store_result}

        # Verify final output
        assert store_result["itemsWritten"] == len(records)
        assert store_result["tableName"] == "pipeline-results"

    def test_sdk_call_sequence(self, pipeline_input, handlers):
        """Verify the MockDurableContext records the expected call sequence."""
        ctx = MockDurableContext()

        # FetchRecords step
        fetch_result = ctx.step(lambda _sc: handlers["FetchRecords"](pipeline_input), "FetchRecords")
        records = fetch_result["records"]

        # TransformRecords map
        def map_processor(_ctx, item, _idx, _all):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        ctx.map(records, map_processor, "TransformRecords")

        # StoreResults step
        input_data = {**pipeline_input, "transformed": records}
        ctx.step(lambda _sc: handlers["StoreResults"](input_data), "StoreResults")

        # Verify call order
        assert len(ctx.calls) == 3
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[0].name == "FetchRecords"
        assert ctx.calls[1].operation == "map"
        assert ctx.calls[1].name == "TransformRecords"
        assert ctx.calls[2].operation == "step"
        assert ctx.calls[2].name == "StoreResults"

    def test_map_processes_all_items(self, pipeline_input, handlers):
        """Verify the Map state processes every fetched record."""
        ctx = MockDurableContext()

        fetch_result = handlers["FetchRecords"](pipeline_input)
        records = fetch_result["records"]

        def map_processor(_ctx, item, _idx, _all):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        map_result = ctx.map(records, map_processor, "TransformRecords")
        transformed = map_result.get_results()

        assert len(transformed) == len(records)
        for item in transformed:
            assert item["validated"] is True
            assert "enrichedAt" in item
            assert "hash" in item

    def test_store_results_receives_correct_count(self, pipeline_input, handlers):
        """Verify StoreResults reports the right number of written items."""
        ctx = MockDurableContext()

        fetch_result = handlers["FetchRecords"](pipeline_input)
        records = fetch_result["records"]

        def map_processor(_ctx, item, _idx, _all):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        map_result = ctx.map(records, map_processor, "TransformRecords")
        transformed = map_result.get_results()

        input_data = {
            **pipeline_input,
            "transformed": transformed,
            "config": {"config": {"tableName": "pipeline-results"}},
        }
        store_result = ctx.step(lambda _sc: handlers["StoreResults"](input_data), "StoreResults")

        assert store_result["itemsWritten"] == len(records)
        assert store_result["tableName"] == "pipeline-results"

    def test_pipeline_with_no_records(self, handlers):
        """Pipeline handles gracefully when there are no records to process."""
        ctx = MockDurableContext()

        # Map with empty list
        map_result = ctx.map([], lambda _ctx, x, _i, _a: x, "TransformRecords")
        assert map_result.get_results() == []

        # Store empty
        input_data = {"transformed": [], "config": {"config": {"tableName": "pipeline-results"}}}
        store_result = ctx.step(lambda _sc: handlers["StoreResults"](input_data), "StoreResults")
        assert store_result["itemsWritten"] == 0
