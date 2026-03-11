"""Tests for CDK app generator."""

import json

import pytest

from rsf.cdk.generator import (
    CDKConfig,
    GENERATED_MARKER,
    generate_cdk,
    sanitize_stack_name,
)


@pytest.fixture
def minimal_config():
    """Minimal CDK configuration for testing."""
    return CDKConfig(workflow_name="MyWorkflow")


@pytest.fixture
def full_config():
    """Full CDK configuration with all optional resources."""
    return CDKConfig(
        workflow_name="OrderProcessor",
        aws_region="us-east-2",
        triggers=[
            {"type": "sqs", "queue_name": "order-queue", "batch_size": 5},
        ],
        has_sqs_triggers=True,
        dynamodb_tables=[
            {
                "table_name": "orders",
                "partition_key": {"name": "order_id", "type": "S"},
                "billing_mode": "PAY_PER_REQUEST",
            },
        ],
        has_dynamodb_tables=True,
        alarms=[
            {
                "type": "Errors",
                "threshold": 1,
                "period": 300,
                "evaluation_periods": 1,
                "sns_topic_arn": "arn:aws:sns:us-east-2:123456:alerts",
            },
        ],
        has_alarms=True,
        dlq_enabled=True,
        dlq_queue_name="order-dlq",
        lambda_url_enabled=True,
        lambda_url_auth_type="NONE",
        timeout_seconds=300,
        stage="prod",
    )


class TestGenerateCDK:
    """Tests for CDK app generation."""

    def test_creates_all_files(self, tmp_path, minimal_config):
        """Generator creates app.py, stack.py, cdk.json, requirements.txt."""
        result = generate_cdk(minimal_config, tmp_path)

        expected_files = {"app.py", "stack.py", "cdk.json", "requirements.txt"}
        generated_names = {f.name for f in result.generated_files}
        assert generated_names == expected_files

        for name in expected_files:
            assert (tmp_path / name).exists()

    def test_creates_output_dir(self, tmp_path, minimal_config):
        """Generator creates output directory if it doesn't exist."""
        output = tmp_path / "cdk" / "nested"
        result = generate_cdk(minimal_config, output)
        assert output.exists()
        assert len(result.generated_files) == 4

    def test_generation_gap_skips_user_edited_file(self, tmp_path, minimal_config):
        """Existing user-edited file (no marker) is skipped."""
        # Create a user-edited app.py (no GENERATED_MARKER)
        user_file = tmp_path / "app.py"
        user_file.write_text("# My custom CDK app\nimport aws_cdk\n", encoding="utf-8")

        result = generate_cdk(minimal_config, tmp_path)

        assert user_file in result.skipped_files
        # Original content preserved
        content = user_file.read_text(encoding="utf-8")
        assert content.startswith("# My custom CDK app")

    def test_generation_gap_overwrites_generated_file(self, tmp_path, minimal_config):
        """Existing file with GENERATED_MARKER is overwritten."""
        generated_file = tmp_path / "app.py"
        generated_file.write_text(f"{GENERATED_MARKER}\n# old content\n", encoding="utf-8")

        result = generate_cdk(minimal_config, tmp_path)

        assert generated_file in result.generated_files
        content = generated_file.read_text(encoding="utf-8")
        assert "RsfStack" in content  # New content

    def test_config_files_always_overwritten(self, tmp_path, minimal_config):
        """cdk.json and requirements.txt are always overwritten (no Generation Gap)."""
        # Create existing files without marker
        (tmp_path / "cdk.json").write_text('{"custom": true}', encoding="utf-8")
        (tmp_path / "requirements.txt").write_text("custom-dep==1.0", encoding="utf-8")

        result = generate_cdk(minimal_config, tmp_path)

        # Both should be in generated_files (overwritten)
        generated_names = {f.name for f in result.generated_files}
        assert "cdk.json" in generated_names
        assert "requirements.txt" in generated_names

    def test_app_py_generated_marker(self, tmp_path, minimal_config):
        """Generated app.py starts with GENERATED_MARKER."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "app.py").read_text(encoding="utf-8")
        assert content.startswith(GENERATED_MARKER)

    def test_stack_py_generated_marker(self, tmp_path, minimal_config):
        """Generated stack.py starts with GENERATED_MARKER."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert content.startswith(GENERATED_MARKER)

    def test_app_py_content(self, tmp_path, minimal_config):
        """Generated app.py imports stack and calls app.synth()."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "app.py").read_text(encoding="utf-8")
        assert "import aws_cdk as cdk" in content
        assert "from stack import RsfStack" in content
        assert "RsfStack(app," in content
        assert "app.synth()" in content

    def test_cdk_json_content(self, tmp_path, minimal_config):
        """Generated cdk.json points to python3 app.py."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "cdk.json").read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["app"] == "python3 app.py"

    def test_requirements_txt_content(self, tmp_path, minimal_config):
        """Generated requirements.txt includes CDK dependencies."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "requirements.txt").read_text(encoding="utf-8")
        assert "aws-cdk-lib>=2.0.0" in content
        assert "constructs>=10.0.0" in content

    def test_minimal_config_no_optional_resources(self, tmp_path, minimal_config):
        """Minimal config produces stack without optional resource blocks."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        # Should have Lambda and IAM
        assert "lambda_.Function" in content
        assert "iam.Role" in content
        assert "logs.LogGroup" in content
        # Should NOT have optional resources
        assert "sqs.Queue" not in content
        assert "dynamodb.Table" not in content

    def test_with_sqs_triggers(self, tmp_path):
        """SQS trigger block appears in stack.py when configured."""
        config = CDKConfig(
            workflow_name="test",
            triggers=[{"type": "sqs", "queue_name": "my-queue", "batch_size": 10}],
            has_sqs_triggers=True,
        )
        generate_cdk(config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert "aws_sqs as sqs" in content
        assert "event_sources" in content
        assert "my-queue" in content or "my_queue" in content

    def test_with_dynamodb(self, tmp_path):
        """DynamoDB table block appears in stack.py when configured."""
        config = CDKConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "items",
                    "partition_key": {"name": "pk", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                },
            ],
            has_dynamodb_tables=True,
        )
        generate_cdk(config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert "aws_dynamodb as dynamodb" in content
        assert "dynamodb.Table" in content
        assert "items" in content

    def test_with_dlq(self, tmp_path):
        """DLQ block appears in stack.py when configured."""
        config = CDKConfig(
            workflow_name="test",
            dlq_enabled=True,
            dlq_queue_name="test-dlq",
        )
        generate_cdk(config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert "DeadLetterQueue" in content
        assert "test-dlq" in content

    def test_with_lambda_url(self, tmp_path):
        """Lambda URL block appears in stack.py when configured."""
        config = CDKConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="NONE",
        )
        generate_cdk(config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert "add_function_url" in content
        assert "NONE" in content

    def test_full_config(self, tmp_path, full_config):
        """Full config with all features produces valid stack."""
        result = generate_cdk(full_config, tmp_path)
        assert len(result.generated_files) == 4
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        # All optional blocks present
        assert "aws_sqs as sqs" in content
        assert "aws_dynamodb as dynamodb" in content
        assert "add_function_url" in content
        assert "DeadLetterQueue" in content

    def test_stack_class_name(self, tmp_path, minimal_config):
        """Stack class is named RsfStack."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "stack.py").read_text(encoding="utf-8")
        assert "class RsfStack(Stack):" in content

    def test_stack_id_derived_from_workflow(self, tmp_path, minimal_config):
        """Stack ID is derived from workflow name."""
        generate_cdk(minimal_config, tmp_path)
        content = (tmp_path / "app.py").read_text(encoding="utf-8")
        assert '"rsf-my-workflow"' in content


class TestSanitizeStackName:
    """Tests for stack name sanitization."""

    def test_pascal_case(self):
        assert sanitize_stack_name("MyWorkflow") == "my-workflow"

    def test_camel_case(self):
        assert sanitize_stack_name("myWorkflow") == "my-workflow"

    def test_kebab_case(self):
        assert sanitize_stack_name("my-workflow") == "my-workflow"

    def test_snake_case(self):
        assert sanitize_stack_name("my_workflow") == "my-workflow"

    def test_with_version(self):
        assert sanitize_stack_name("ProcessOrderV2") == "process-order-v2"

    def test_special_chars_removed(self):
        assert sanitize_stack_name("my.workflow!v2") == "myworkflowv2"

    def test_multiple_hyphens_collapsed(self):
        assert sanitize_stack_name("my--workflow") == "my-workflow"

    def test_leading_trailing_hyphens_stripped(self):
        assert sanitize_stack_name("-workflow-") == "workflow"

    def test_simple_lowercase(self):
        assert sanitize_stack_name("simple") == "simple"
