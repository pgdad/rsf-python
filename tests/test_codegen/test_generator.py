"""Tests for the code generator."""

import hashlib
from pathlib import Path

import pytest

from rsf.codegen.engine import topyrepr
from rsf.codegen.generator import (
    GENERATED_MARKER,
    _should_overwrite,
    _to_snake_case,
    generate,
    render_handler_stub,
    render_orchestrator,
)
from rsf.codegen.state_mappers import map_states
from rsf.dsl.parser import load_definition


class TestTopyrepr:
    def test_none(self):
        assert topyrepr(None) == "None"

    def test_true(self):
        assert topyrepr(True) == "True"

    def test_false(self):
        assert topyrepr(False) == "False"

    def test_string(self):
        assert topyrepr("hello") == "'hello'"

    def test_string_with_quotes(self):
        result = topyrepr("it's")
        assert result == '"it\'s"'

    def test_integer(self):
        assert topyrepr(42) == "42"

    def test_float(self):
        assert topyrepr(3.14) == "3.14"

    def test_list(self):
        assert topyrepr([1, "a", True]) == "[1, 'a', True]"

    def test_empty_list(self):
        assert topyrepr([]) == "[]"

    def test_dict(self):
        result = topyrepr({"key": "value"})
        assert result == "{'key': 'value'}"

    def test_nested(self):
        result = topyrepr({"items": [1, None, {"x": True}]})
        assert "None" in result
        assert "True" in result


class TestToSnakeCase:
    def test_pascal_case(self):
        assert _to_snake_case("ValidateOrder") == "validate_order"

    def test_camel_case(self):
        assert _to_snake_case("validateOrder") == "validate_order"

    def test_single_word(self):
        assert _to_snake_case("Process") == "process"

    def test_multiple_caps(self):
        assert _to_snake_case("HTTPRequest") == "http_request"

    def test_already_snake(self):
        assert _to_snake_case("already_snake") == "already_snake"


class TestShouldOverwrite:
    def test_nonexistent_file(self, tmp_path):
        assert _should_overwrite(tmp_path / "nope.py") is True

    def test_file_with_marker(self, tmp_path):
        f = tmp_path / "gen.py"
        f.write_text(f"{GENERATED_MARKER} v0.1.0 on 2024-01-01\ncode here\n")
        assert _should_overwrite(f) is True

    def test_file_without_marker(self, tmp_path):
        f = tmp_path / "user.py"
        f.write_text("# My custom handler\ndef handle(data):\n    return data\n")
        assert _should_overwrite(f) is False

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        assert _should_overwrite(f) is False


class TestRenderHandlerStub:
    def test_basic_stub(self):
        code = render_handler_stub("ValidateOrder")
        assert '@state("ValidateOrder")' in code
        assert "def validate_order(input_data: dict)" in code
        assert "raise NotImplementedError" in code

    def test_stub_has_docstring(self):
        code = render_handler_stub("ProcessPayment")
        assert "ProcessPayment" in code
        assert "Implement your business logic" in code


class TestRenderOrchestrator:
    @pytest.fixture
    def simple_workflow(self, tmp_path):
        dsl = tmp_path / "workflow.yaml"
        dsl.write_text('rsf_version: "1.0"\nStartAt: DoWork\nStates:\n  DoWork:\n    Type: Task\n    End: true\n')
        return dsl

    def test_header_has_marker(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        assert code.startswith(GENERATED_MARKER)

    def test_header_has_hash(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        expected_hash = hashlib.sha256(simple_workflow.read_bytes()).hexdigest()
        assert expected_hash in code

    def test_header_has_version(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow, rsf_version="1.2.3")
        assert "RSF v1.2.3" in code

    def test_imports_present(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        assert "from aws_lambda_durable_execution_sdk_python" in code
        assert "from rsf.registry import get_handler" in code
        assert "import handlers.do_work" in code

    def test_workflow_error_class(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        assert "class WorkflowError(Exception):" in code

    def test_startup_hooks(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        assert "_startup_done" in code
        assert "get_startup_hooks()" in code

    def test_state_machine_loop(self, simple_workflow):
        sm = load_definition(simple_workflow)
        mappings = map_states(sm)
        code = render_orchestrator(sm, mappings, simple_workflow)
        assert "current_state = 'DoWork'" in code
        assert "while current_state is not None:" in code
        assert "if current_state == 'DoWork':" in code


class TestGenerate:
    @pytest.fixture
    def workflow_dir(self, tmp_path):
        dsl = tmp_path / "workflow.yaml"
        dsl.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: DoWork\n"
            "States:\n"
            "  DoWork:\n"
            "    Type: Task\n"
            "    Next: Done\n"
            "  Done:\n"
            "    Type: Succeed\n"
        )
        return tmp_path

    def test_creates_orchestrator(self, workflow_dir):
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        result = generate(sm, dsl, workflow_dir / "output")
        assert result.orchestrator_path.exists()
        assert result.orchestrator_path.name == "orchestrator.py"

    def test_creates_handler_stubs(self, workflow_dir):
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        result = generate(sm, dsl, workflow_dir / "output")
        assert len(result.handler_paths) == 1
        handler = result.handler_paths[0]
        assert handler.name == "do_work.py"
        assert "@state" in handler.read_text()

    def test_handler_not_overwritten(self, workflow_dir):
        """Existing user-modified handler files are not overwritten."""
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        handlers_dir = workflow_dir / "output" / "handlers"
        handlers_dir.mkdir(parents=True)
        user_handler = handlers_dir / "do_work.py"
        user_handler.write_text("# My custom handler\ndef my_handler(data):\n    return data\n")

        result = generate(sm, dsl, workflow_dir / "output")
        assert len(result.skipped_handlers) == 1
        # Original content preserved
        assert "My custom handler" in user_handler.read_text()

    def test_orchestrator_always_overwritten(self, workflow_dir):
        """Orchestrator is always regenerated (has marker)."""
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        output_dir = workflow_dir / "output"

        # First generation
        result1 = generate(sm, dsl, output_dir)
        content1 = result1.orchestrator_path.read_text()

        # Second generation (should overwrite)
        result2 = generate(sm, dsl, output_dir)
        content2 = result2.orchestrator_path.read_text()

        # Both should have the marker
        assert content1.startswith(GENERATED_MARKER)
        assert content2.startswith(GENERATED_MARKER)

    def test_replay_safety(self, workflow_dir):
        """Running generation twice with same DSL produces identical output (except timestamp)."""
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        output_dir = workflow_dir / "output"

        result1 = generate(sm, dsl, output_dir)
        content1 = result1.orchestrator_path.read_text()

        # Remove timestamp line for comparison
        lines1 = [l for l in content1.split("\n") if "on 20" not in l]

        result2 = generate(sm, dsl, output_dir)
        content2 = result2.orchestrator_path.read_text()
        lines2 = [l for l in content2.split("\n") if "on 20" not in l]

        assert lines1 == lines2

    def test_creates_handlers_init(self, workflow_dir):
        dsl = workflow_dir / "workflow.yaml"
        sm = load_definition(dsl)
        result = generate(sm, dsl, workflow_dir / "output")
        init_path = workflow_dir / "output" / "handlers" / "__init__.py"
        assert init_path.exists()
        assert "do_work" in init_path.read_text()


class TestGenerateAllStateTypes:
    """Test generation against the all_state_types fixture."""

    @pytest.fixture
    def all_types_fixture(self):
        return Path(__file__).parent.parent.parent / "fixtures" / "valid" / "all_state_types.yaml"

    def test_generates_without_error(self, all_types_fixture, tmp_path):
        sm = load_definition(all_types_fixture)
        result = generate(sm, all_types_fixture, tmp_path / "output")
        assert result.orchestrator_path.exists()

    def test_all_task_states_have_handlers(self, all_types_fixture, tmp_path):
        sm = load_definition(all_types_fixture)
        result = generate(sm, all_types_fixture, tmp_path / "output")
        # InitTask + ProcessA + ProcessB + ProcessOne = 4 Task states
        # (ProcessA, ProcessB, ProcessOne are in branches - not in BFS of top level)
        # Top level tasks: InitTask
        assert len(result.handler_paths) >= 1

    def test_orchestrator_contains_all_reachable_states(self, all_types_fixture, tmp_path):
        sm = load_definition(all_types_fixture)
        result = generate(sm, all_types_fixture, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        # All states reachable from BFS should appear
        assert "'InitTask'" in code
        assert "'InjectData'" in code
        assert "'WaitForApproval'" in code
        assert "'RouteDecision'" in code
        assert "'ProcessBoth'" in code
        assert "'ProcessItems'" in code
        assert "'Done'" in code
        assert "'OrderFailed'" in code
        assert "'HandleError'" in code

    def test_orchestrator_has_helper_functions(self, all_types_fixture, tmp_path):
        sm = load_definition(all_types_fixture)
        result = generate(sm, all_types_fixture, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        assert "def _resolve_path" in code
        assert "def _apply_result_path" in code
        assert "def _apply_error_result" in code


class TestGenerateChoiceWorkflow:
    """Test generation for the choice workflow fixture."""

    @pytest.fixture
    def choice_fixture(self):
        return Path(__file__).parent.parent.parent / "fixtures" / "valid" / "choice_workflow.yaml"

    def test_choice_conditions_generated(self, choice_fixture, tmp_path):
        sm = load_definition(choice_fixture)
        result = generate(sm, choice_fixture, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        assert "'RoutePayment'" in code
        # Should have conditional routing
        assert "if " in code
        assert "'HighValueApproval'" in code
        assert "'ProcessRefund'" in code
        assert "'AutoApprove'" in code
        assert "'ManualReview'" in code
