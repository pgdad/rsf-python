"""Local tests for workflow YAML parsing and handler registration (TEST-01)."""

from pathlib import Path

from rsf.dsl.parser import load_definition
from rsf.registry.registry import discover_handlers, registered_states

EXAMPLE_ROOT = Path(__file__).parent.parent


class TestWorkflowParsing:
    """Tests that verify workflow.yaml parses into a valid StateMachineDefinition."""

    def test_workflow_yaml_parses_without_error(self):
        """load_definition returns a non-None StateMachineDefinition."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition is not None

    def test_workflow_start_at_is_validate_image(self):
        """StartAt field must be ValidateImage as defined in workflow.yaml."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.start_at == "ValidateImage"

    def test_workflow_has_all_six_states(self):
        """All 6 states must be present: 4 Task states + ProcessingComplete + ProcessingFailed."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        expected_states = {
            "ValidateImage",
            "ResizeImage",
            "AnalyzeContent",
            "CatalogueImage",
            "ProcessingComplete",
            "ProcessingFailed",
        }
        assert set(definition.states.keys()) == expected_states

    def test_workflow_has_dynamodb_table_config(self):
        """workflow.yaml must declare at least one DynamoDB table."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.dynamodb_tables is not None
        assert len(definition.dynamodb_tables) >= 1

    def test_workflow_has_dlq_config(self):
        """workflow.yaml must declare a dead_letter_queue with enabled=True."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.dead_letter_queue is not None
        assert definition.dead_letter_queue.enabled is True


class TestHandlerRegistration:
    """Tests that verify discover_handlers() correctly registers all 4 Task handlers."""

    def test_discover_handlers_finds_all_four(self):
        """discover_handlers must register all 4 Task handler state names."""
        discover_handlers(EXAMPLE_ROOT / "handlers")
        states = registered_states()
        expected = {"ValidateImage", "ResizeImage", "AnalyzeContent", "CatalogueImage"}
        assert expected.issubset(states)

    def test_discover_handlers_registers_exactly_four(self):
        """discover_handlers must register exactly 4 handlers — no spurious registrations."""
        discover_handlers(EXAMPLE_ROOT / "handlers")
        assert len(registered_states()) == 4

    def test_registered_states_type(self):
        """registered_states() must return a frozenset."""
        discover_handlers(EXAMPLE_ROOT / "handlers")
        assert isinstance(registered_states(), frozenset)
