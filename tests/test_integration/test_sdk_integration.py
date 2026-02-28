"""SDK integration tests — execute generated orchestrator code via MockDurableContext.

These tests generate real orchestrator code from DSL workflows, then execute
it using the MockDurableContext to verify correct state transitions and output.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from rsf.codegen.generator import generate, render_orchestrator
from rsf.codegen.state_mappers import map_states
from rsf.dsl.parser import load_definition, parse_definition
from rsf.registry import clear, clear_startup_hooks, state

from tests.mock_sdk import MockDurableContext, Duration, BranchResult


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _build_and_exec(sm, dsl_path, ctx, event, handlers=None):
    """Generate orchestrator code and execute it with the mock context.

    Args:
        sm: Parsed StateMachineDefinition.
        dsl_path: Path to the DSL YAML file (for hash computation).
        ctx: MockDurableContext instance.
        event: Input event dict.
        handlers: Dict of state_name -> handler function to register.

    Returns:
        The return value of the orchestrator function.
    """
    clear()
    clear_startup_hooks()

    # Register handlers
    if handlers:
        for name, fn in handlers.items():
            state(name)(fn)

    mappings = map_states(sm)
    code = render_orchestrator(sm, mappings, dsl_path)

    # Create a mock SDK module
    mock_sdk = types.ModuleType("aws_lambda_durable_execution_sdk_python")
    mock_sdk.DurableContext = MockDurableContext
    mock_sdk.durable_execution = lambda f: f  # No-op decorator

    mock_config = types.ModuleType("aws_lambda_durable_execution_sdk_python.config")
    mock_config.Duration = Duration

    sys.modules["aws_lambda_durable_execution_sdk_python"] = mock_sdk
    sys.modules["aws_lambda_durable_execution_sdk_python.config"] = mock_config

    try:
        # Strip handler import lines (they reference files that don't exist in tests)
        import re

        code = re.sub(r"^import handlers\.\w+\n", "", code, flags=re.MULTILINE)

        # Execute the generated code in a namespace
        namespace = {}
        exec(compile(code, f"<orchestrator:{dsl_path.stem}>", "exec"), namespace)

        # Call the lambda_handler with our mock context
        result = namespace["lambda_handler"](ctx, event)
        return result
    finally:
        sys.modules.pop("aws_lambda_durable_execution_sdk_python", None)
        sys.modules.pop("aws_lambda_durable_execution_sdk_python.config", None)
        clear()
        clear_startup_hooks()


class TestSimpleTaskWorkflow:
    """Execute a simple Task -> Succeed workflow."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: DoWork\n"
            "States:\n"
            "  DoWork:\n"
            "    Type: Task\n"
            "    Next: Done\n"
            "  Done:\n"
            "    Type: Succeed\n"
        )
        return f

    def test_executes_handler_and_returns(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        ctx.override_step("DoWork", {"processed": True})

        result = _build_and_exec(
            sm,
            workflow,
            ctx,
            {"input": "data"},
            handlers={"DoWork": lambda x: {"processed": True}},
        )

        assert result == {"processed": True}
        assert len(ctx.calls) == 1
        assert ctx.calls[0].name == "DoWork"

    def test_handler_receives_input(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()

        captured = {}

        def handler(data):
            captured.update(data)
            return {"done": True}

        result = _build_and_exec(
            sm,
            workflow,
            ctx,
            {"key": "value"},
            handlers={"DoWork": handler},
        )

        assert captured == {"key": "value"}


class TestTaskChainWorkflow:
    """Execute a chain of Task states."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: Step1\n"
            "States:\n"
            "  Step1:\n"
            "    Type: Task\n"
            "    Next: Step2\n"
            "  Step2:\n"
            "    Type: Task\n"
            "    Next: Step3\n"
            "  Step3:\n"
            "    Type: Task\n"
            "    End: true\n"
        )
        return f

    def test_all_three_steps_execute(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()

        result = _build_and_exec(
            sm,
            workflow,
            ctx,
            {"n": 0},
            handlers={
                "Step1": lambda x: {"n": x["n"] + 1},
                "Step2": lambda x: {"n": x["n"] + 10},
                "Step3": lambda x: {"n": x["n"] + 100},
            },
        )

        assert result == {"n": 111}
        assert len(ctx.calls) == 3
        assert [c.name for c in ctx.calls] == ["Step1", "Step2", "Step3"]


class TestPassStateWorkflow:
    """Execute workflows with Pass states."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: Inject\n"
            "States:\n"
            "  Inject:\n"
            "    Type: Pass\n"
            "    Result:\n"
            "      injected: true\n"
            "    End: true\n"
        )
        return f

    def test_pass_injects_result(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        result = _build_and_exec(sm, workflow, ctx, {})
        assert result == {"injected": True}


class TestChoiceWorkflow:
    """Execute workflows with Choice states."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: Route\n"
            "States:\n"
            "  Route:\n"
            "    Type: Choice\n"
            "    Choices:\n"
            "      - Variable: $.amount\n"
            "        NumericGreaterThan: 100\n"
            "        Next: High\n"
            "    Default: Low\n"
            "  High:\n"
            "    Type: Pass\n"
            "    Result:\n"
            "      tier: high\n"
            "    End: true\n"
            "  Low:\n"
            "    Type: Pass\n"
            "    Result:\n"
            "      tier: low\n"
            "    End: true\n"
        )
        return f

    def test_choice_takes_matching_branch(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        result = _build_and_exec(sm, workflow, ctx, {"amount": 200})
        assert result == {"tier": "high"}

    def test_choice_takes_default(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        result = _build_and_exec(sm, workflow, ctx, {"amount": 50})
        assert result == {"tier": "low"}


class TestWaitWorkflow:
    """Execute workflows with Wait states."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: WaitABit\n"
            "States:\n"
            "  WaitABit:\n"
            "    Type: Wait\n"
            "    Seconds: 60\n"
            "    Next: Done\n"
            "  Done:\n"
            "    Type: Succeed\n"
        )
        return f

    def test_wait_records_duration(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        result = _build_and_exec(sm, workflow, ctx, {"data": 1})
        assert result == {"data": 1}
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "wait"
        assert ctx.calls[0].duration.value == 60


class TestFailWorkflow:
    """Execute workflows with Fail states."""

    @pytest.fixture
    def workflow(self, tmp_path):
        f = tmp_path / "workflow.yaml"
        f.write_text(
            'rsf_version: "1.0"\n'
            "StartAt: Boom\n"
            "States:\n"
            "  Boom:\n"
            "    Type: Fail\n"
            "    Error: CustomError\n"
            "    Cause: Something went wrong\n"
        )
        return f

    def test_fail_raises_workflow_error(self, workflow):
        sm = load_definition(workflow)
        ctx = MockDurableContext()
        with pytest.raises(Exception, match="CustomError"):
            _build_and_exec(sm, workflow, ctx, {})


class TestParallelWorkflow:
    """Execute workflows with Parallel states — key success criteria."""

    @pytest.fixture
    def workflow(self):
        return FIXTURES_DIR / "valid" / "parallel_workflow.yaml"

    def test_parallel_generates_and_compiles(self, workflow, tmp_path):
        """Parallel workflow generates valid, compilable code."""
        sm = load_definition(workflow)
        result = generate(sm, workflow, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        compile(code, "parallel_test", "exec")

    def test_parallel_state_in_code(self, workflow, tmp_path):
        """Generated code contains parallel SDK calls."""
        sm = load_definition(workflow)
        result = generate(sm, workflow, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        assert "context.parallel" in code
        assert "_run_branch_" in code


class TestMapWorkflow:
    """Execute workflows with Map states — key success criteria."""

    @pytest.fixture
    def workflow(self):
        return FIXTURES_DIR / "valid" / "map_workflow.yaml"

    def test_map_generates_and_compiles(self, workflow, tmp_path):
        """Map workflow generates valid, compilable code."""
        sm = load_definition(workflow)
        result = generate(sm, workflow, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        compile(code, "map_test", "exec")

    def test_map_state_in_code(self, workflow, tmp_path):
        """Generated code contains map SDK calls."""
        sm = load_definition(workflow)
        result = generate(sm, workflow, tmp_path / "output")
        code = result.orchestrator_path.read_text()
        assert "context.map" in code
        assert "_run_map_" in code


class TestFixtureConformance:
    """Verify all valid fixture files generate executable orchestrators."""

    @pytest.mark.parametrize(
        "fixture",
        sorted(FIXTURES_DIR.glob("valid/*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_fixture_generates_valid_code(self, fixture, tmp_path):
        """All valid fixtures should generate without error."""
        sm = load_definition(fixture)
        result = generate(sm, fixture, tmp_path / "output")
        assert result.orchestrator_path.exists()
        code = result.orchestrator_path.read_text()
        # Verify the code compiles (no syntax errors)
        compile(code, str(result.orchestrator_path), "exec")

    @pytest.mark.parametrize(
        "fixture",
        sorted((FIXTURES_DIR / "invalid" / "pydantic").glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_invalid_pydantic_fixtures_rejected(self, fixture):
        """Pydantic-invalid fixtures should raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            load_definition(fixture)

    @pytest.mark.parametrize(
        "fixture",
        sorted((FIXTURES_DIR / "invalid" / "semantic").glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_invalid_semantic_fixtures_have_errors(self, fixture):
        """Semantic-invalid fixtures should produce validation errors."""
        from rsf.dsl.validator import validate_definition

        sm = load_definition(fixture)
        errors = validate_definition(sm)
        assert len(errors) > 0
