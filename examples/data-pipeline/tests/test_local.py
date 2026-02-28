"""Local tests for the data-pipeline example.

Tests cover:
1. Workflow YAML parsing via rsf.dsl.parser.load_definition
2. Individual handler unit tests
3. I/O processing features present in the YAML
4. Full pipeline simulation using MockDurableContext
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


# ---------------------------------------------------------------------------
# 2. Individual handler unit tests
# ---------------------------------------------------------------------------


class TestFetchRecordsHandler:
    """Unit tests for the FetchRecords handler."""

    def test_returns_items_and_count(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({"bucket": "my-bucket", "prefix": "data/"})
        assert "items" in result
        assert "totalCount" in result
        assert isinstance(result["items"], list)
        assert result["totalCount"] == len(result["items"])

    def test_items_have_expected_structure(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({"bucket": "test-bucket", "prefix": "input/"})
        for item in result["items"]:
            assert "id" in item
            assert "value" in item
            assert "source" in item
            assert item["source"].startswith("s3://test-bucket/input/")

    def test_respects_max_items(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({"bucket": "b", "prefix": "p/", "maxItems": 3})
        assert result["totalCount"] <= 3

    def test_default_values(self):
        from handlers.fetch_records import fetch_records

        result = fetch_records({})
        assert result["totalCount"] > 0
        assert result["items"][0]["source"].startswith("s3://default-bucket/data/")


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
        # ISO format timestamp check
        assert "T" in result["enrichedAt"]

    def test_adds_hash(self):
        from handlers.enrich_record import enrich_record

        record = {"id": "rec-1", "value": 42, "validated": True}
        result = enrich_record(record)
        assert "hash" in result
        assert len(result["hash"]) == 16  # 16 hex chars

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
        result = store_results({"tableName": "my-table", "items": items})
        assert result["itemsWritten"] == 3
        assert result["tableName"] == "my-table"

    def test_empty_items(self):
        from handlers.store_results import store_results

        result = store_results({"tableName": "t", "items": []})
        assert result["itemsWritten"] == 0

    def test_default_table_name(self):
        from handlers.store_results import store_results

        result = store_results({"items": [{"id": "1"}]})
        assert result["tableName"] == "unknown-table"
        assert result["itemsWritten"] == 1


# ---------------------------------------------------------------------------
# 3. I/O processing features in YAML
# ---------------------------------------------------------------------------


class TestIOProcessingFeatures:
    """Verify that the workflow YAML uses I/O processing features."""

    @pytest.fixture
    def sm(self):
        return load_definition(WORKFLOW_PATH)

    def test_init_pipeline_has_result(self, sm):
        init = sm.states["InitPipeline"]
        assert init.result is not None
        assert init.result["pipeline"] == "etl-v1"

    def test_init_pipeline_has_parameters(self, sm):
        init = sm.states["InitPipeline"]
        assert init.parameters is not None
        assert init.parameters["config"]["tableName"] == "pipeline-results"

    def test_init_pipeline_has_result_path(self, sm):
        init = sm.states["InitPipeline"]
        assert init.result_path == "$.config"

    def test_fetch_records_has_input_path(self, sm):
        fetch = sm.states["FetchRecords"]
        assert fetch.input_path == "$.source"

    def test_fetch_records_has_parameters(self, sm):
        fetch = sm.states["FetchRecords"]
        assert fetch.parameters is not None
        assert "bucket.$" in fetch.parameters
        assert "prefix.$" in fetch.parameters
        assert fetch.parameters["maxItems"] == 100

    def test_fetch_records_has_result_selector(self, sm):
        fetch = sm.states["FetchRecords"]
        assert fetch.result_selector is not None
        assert "records.$" in fetch.result_selector
        assert "count.$" in fetch.result_selector

    def test_fetch_records_has_result_path(self, sm):
        fetch = sm.states["FetchRecords"]
        assert fetch.result_path == "$.fetched"

    def test_transform_records_has_items_path(self, sm):
        xform = sm.states["TransformRecords"]
        assert xform.items_path == "$.fetched.records"

    def test_transform_records_has_result_path(self, sm):
        xform = sm.states["TransformRecords"]
        assert xform.result_path == "$.transformed"

    def test_store_results_has_input_path(self, sm):
        store = sm.states["StoreResults"]
        assert store.input_path == "$"

    def test_store_results_has_parameters(self, sm):
        store = sm.states["StoreResults"]
        assert store.parameters is not None
        assert "tableName.$" in store.parameters
        assert "items.$" in store.parameters

    def test_store_results_has_result_path(self, sm):
        store = sm.states["StoreResults"]
        assert store.result_path == "$.stored"

    def test_store_results_has_output_path(self, sm):
        store = sm.states["StoreResults"]
        assert store.output_path == "$.stored"


# ---------------------------------------------------------------------------
# 4. Full pipeline simulation with MockDurableContext
# ---------------------------------------------------------------------------


class TestFullPipelineSimulation:
    """End-to-end pipeline simulation using MockDurableContext.

    Simulates the full pipeline flow:
      InitPipeline (Pass) -> FetchRecords -> TransformRecords (Map) ->
      StoreResults -> PipelineComplete (Pass)
    """

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

        # --- Step 1: InitPipeline (Pass state) ---
        # A Pass state with Parameters produces the Parameters value,
        # placed at ResultPath on the raw input.
        init_result = {
            "config": {
                "batchSize": 10,
                "tableName": "pipeline-results",
            }
        }
        data = {**pipeline_input, "config": init_result}

        # --- Step 2: FetchRecords (Task state) ---
        # InputPath: $.source  -> extracts source object
        # Parameters: resolves bucket.$ and prefix.$ from source
        fetch_input = {
            "bucket": pipeline_input["source"]["bucket"],
            "prefix": pipeline_input["source"]["prefix"],
            "maxItems": 100,
        }
        fetch_raw_result = ctx.step("FetchRecords", handlers["FetchRecords"], fetch_input)

        # ResultSelector picks records.$ and count.$
        fetch_selected = {
            "records": fetch_raw_result["items"],
            "count": fetch_raw_result["totalCount"],
        }
        # ResultPath: $.fetched -> merge into data
        data["fetched"] = fetch_selected

        # --- Step 3: TransformRecords (Map state) ---
        # ItemsPath: $.fetched.records -> iterate over records
        records = data["fetched"]["records"]

        def map_item_processor(item):
            validated = handlers["ValidateRecord"](item)
            enriched = handlers["EnrichRecord"](validated)
            return enriched

        map_result = ctx.map(
            "TransformRecords",
            map_item_processor,
            records,
            max_concurrency=5,
        )
        transformed = map_result.get_results()
        # ResultPath: $.transformed
        data["transformed"] = transformed

        # --- Step 4: StoreResults (Task state) ---
        # Parameters: resolves tableName.$ and items.$ from data
        store_input = {
            "tableName": data["config"]["config"]["tableName"],
            "items": data["transformed"],
        }
        store_result = ctx.step("StoreResults", handlers["StoreResults"], store_input)
        # ResultPath: $.stored, OutputPath: $.stored -> final output
        data["stored"] = store_result

        # --- Step 5: PipelineComplete (Pass state, End: true) ---
        final_output = data["stored"]

        # Assertions on final output
        assert final_output["itemsWritten"] == len(records)
        assert final_output["tableName"] == "pipeline-results"

    def test_sdk_call_sequence(self, pipeline_input, handlers):
        """Verify the MockDurableContext records the expected call sequence."""
        ctx = MockDurableContext()

        # FetchRecords step
        fetch_input = {
            "bucket": "data-lake",
            "prefix": "incoming/2026-02-26/",
            "maxItems": 100,
        }
        fetch_result = ctx.step("FetchRecords", handlers["FetchRecords"], fetch_input)
        records = fetch_result["items"]

        # TransformRecords map
        def map_processor(item):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        ctx.map("TransformRecords", map_processor, records, max_concurrency=5)

        # StoreResults step
        store_input = {"tableName": "pipeline-results", "items": records}
        ctx.step("StoreResults", handlers["StoreResults"], store_input)

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

        fetch_result = handlers["FetchRecords"]({"bucket": "data-lake", "prefix": "incoming/", "maxItems": 100})
        records = fetch_result["items"]

        def map_processor(item):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        map_result = ctx.map("TransformRecords", map_processor, records)
        transformed = map_result.get_results()

        assert len(transformed) == len(records)
        for item in transformed:
            assert item["validated"] is True
            assert "enrichedAt" in item
            assert "hash" in item

    def test_store_results_receives_correct_count(self, pipeline_input, handlers):
        """Verify StoreResults reports the right number of written items."""
        ctx = MockDurableContext()

        # Fetch
        fetch_result = handlers["FetchRecords"]({"bucket": "b", "prefix": "p/", "maxItems": 4})
        records = fetch_result["items"]

        # Transform
        def map_processor(item):
            v = handlers["ValidateRecord"](item)
            return handlers["EnrichRecord"](v)

        map_result = ctx.map("TransformRecords", map_processor, records)
        transformed = map_result.get_results()

        # Store
        store_input = {"tableName": "pipeline-results", "items": transformed}
        store_result = ctx.step("StoreResults", handlers["StoreResults"], store_input)

        assert store_result["itemsWritten"] == len(records)
        assert store_result["tableName"] == "pipeline-results"

    def test_pipeline_with_no_records(self, handlers):
        """Pipeline handles gracefully when there are no records to process."""
        ctx = MockDurableContext()

        # Simulate an empty fetch result
        empty_fetch = {"items": [], "totalCount": 0}
        ctx.override_step("FetchRecords", empty_fetch)
        ctx.step("FetchRecords", handlers["FetchRecords"], {})

        # Map with empty list
        map_result = ctx.map("TransformRecords", lambda x: x, [])
        assert map_result.get_results() == []

        # Store empty
        store_input = {"tableName": "pipeline-results", "items": []}
        store_result = ctx.step("StoreResults", handlers["StoreResults"], store_input)
        assert store_result["itemsWritten"] == 0
