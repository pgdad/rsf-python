"""Tests for Terraform generation."""

from pathlib import Path

import pytest

from rsf.terraform.engine import create_hcl_environment, render_hcl_template
from rsf.terraform.generator import (
    GENERATED_MARKER,
    TerraformConfig,
    _should_overwrite,
    derive_iam_statements,
    generate_terraform,
    sanitize_name,
)


class TestSanitizeName:
    def test_pascal_case(self):
        assert sanitize_name("MyWorkflow") == "my_workflow"

    def test_kebab_case(self):
        assert sanitize_name("my-workflow") == "my_workflow"

    def test_camel_case(self):
        assert sanitize_name("processOrder") == "process_order"

    def test_pascal_with_numbers(self):
        assert sanitize_name("ProcessOrderV2") == "process_order_v2"

    def test_already_snake(self):
        assert sanitize_name("my_workflow") == "my_workflow"

    def test_uppercase_acronym(self):
        assert sanitize_name("HTTPHandler") == "http_handler"

    def test_single_word(self):
        assert sanitize_name("Workflow") == "workflow"

    def test_multiple_hyphens(self):
        assert sanitize_name("my--workflow") == "my_workflow"

    def test_leading_digit(self):
        result = sanitize_name("2cool")
        assert result[0].isalpha() or result[0] == "_"

    def test_result_is_valid_terraform_id(self):
        """All sanitized names must be valid Terraform identifiers."""
        test_names = [
            "MyWorkflow",
            "my-workflow",
            "Process_Order",
            "HTTPHandler",
            "simple",
            "a",
        ]
        import re

        for name in test_names:
            result = sanitize_name(name)
            assert re.match(r"^[a-z_][a-z0-9_]*$", result), f"'{name}' → '{result}' is not a valid Terraform identifier"


class TestDeriveIamStatements:
    def test_returns_exactly_3_statements(self):
        statements = derive_iam_statements()
        assert len(statements) == 3

    def test_cloudwatch_logs_statement(self):
        statements = derive_iam_statements()
        cw = statements[0]
        assert cw["sid"] == "CloudWatchLogs"
        assert "logs:CreateLogGroup" in cw["actions"]
        assert "logs:CreateLogStream" in cw["actions"]
        assert "logs:PutLogEvents" in cw["actions"]

    def test_lambda_self_invoke_statement(self):
        statements = derive_iam_statements()
        invoke = statements[1]
        assert invoke["sid"] == "LambdaSelfInvoke"
        assert "lambda:InvokeFunction" in invoke["actions"]

    def test_durable_execution_statement(self):
        statements = derive_iam_statements()
        durable = statements[2]
        assert durable["sid"] == "DurableExecution"
        assert "lambda:CheckpointDurableExecution" in durable["actions"]
        assert "lambda:GetDurableExecution" in durable["actions"]
        assert "lambda:ListDurableExecutionsByFunction" in durable["actions"]


class TestShouldOverwrite:
    def test_nonexistent_file(self, tmp_path):
        assert _should_overwrite(tmp_path / "nope.tf") is True

    def test_file_with_marker(self, tmp_path):
        f = tmp_path / "gen.tf"
        f.write_text(f'{GENERATED_MARKER}\n\nresource "aws_lambda_function" ...\n')
        assert _should_overwrite(f) is True

    def test_file_without_marker(self, tmp_path):
        f = tmp_path / "custom.tf"
        f.write_text('# My custom terraform\nresource "aws_s3_bucket" ...\n')
        assert _should_overwrite(f) is False

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.tf"
        f.write_text("")
        assert _should_overwrite(f) is False


class TestHclEngine:
    def test_custom_delimiters_work(self):
        """Verify that << >> delimiters render correctly."""
        env = create_hcl_environment()
        template = env.from_string("resource_id = << name >>")
        result = template.render(name="my_resource")
        assert result == "resource_id = my_resource"

    def test_block_delimiters_work(self):
        """Verify that <% %> block delimiters work."""
        env = create_hcl_environment()
        template = env.from_string("<% if enabled %>yes<% endif %>")
        assert template.render(enabled=True) == "yes"
        assert template.render(enabled=False) == ""

    def test_terraform_interpolation_preserved(self):
        """Terraform ${} is NOT interpreted by Jinja2 with custom delimiters."""
        env = create_hcl_environment()
        template = env.from_string('name = "${var.name_prefix}-${var.workflow_name}"')
        result = template.render()
        assert "${var.name_prefix}" in result
        assert "${var.workflow_name}" in result

    def test_no_raw_jinja_delimiters_in_output(self):
        """Rendered HCL should not contain << >> or <% %> delimiters."""
        content = render_hcl_template(
            "main.tf.j2",
            resource_id="test_wf",
            workflow_name="test-wf",
        )
        assert "<<" not in content
        assert ">>" not in content
        assert "<%" not in content
        assert "%>" not in content


class TestGenerateTerraform:
    @pytest.fixture
    def config(self):
        return TerraformConfig(
            workflow_name="my-workflow",
            aws_region="us-east-2",
            name_prefix="rsf",
        )

    def test_creates_all_6_files(self, config, tmp_path):
        result = generate_terraform(config, tmp_path)
        assert len(result.generated_files) == 6
        expected_files = {"main.tf", "variables.tf", "iam.tf", "outputs.tf", "cloudwatch.tf", "backend.tf"}
        actual_files = {f.name for f in result.generated_files}
        assert actual_files == expected_files

    def test_main_tf_content(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "main.tf").read_text()
        assert GENERATED_MARKER in content
        assert "aws_lambda_function" in content
        assert "durable_config" in content
        assert "archive_file" in content
        assert "my-workflow" in content  # workflow_name in output_path
        assert "my_workflow" in content  # sanitized resource_id

    def test_variables_tf_content(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "variables.tf").read_text()
        assert "us-east-2" in content
        assert "rsf" in content
        assert "my-workflow" in content
        assert "execution_timeout" in content
        assert "retention_period" in content

    def test_iam_tf_content(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "aws_iam_role" in content
        assert "aws_iam_role_policy" in content
        assert "CloudWatchLogs" in content
        assert "LambdaSelfInvoke" in content
        assert "DurableExecution" in content
        assert "logs:CreateLogGroup" in content
        assert "lambda:InvokeFunction" in content
        assert "lambda:CheckpointDurableExecution" in content

    def test_iam_has_exactly_3_statements(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        # HCL uses Sid = "..." (unquoted key)
        assert content.count("Sid") == 3

    def test_outputs_tf_content(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "outputs.tf").read_text()
        assert "function_arn" in content
        assert "function_name" in content
        assert "role_arn" in content
        assert "log_group_name" in content

    def test_cloudwatch_tf_content(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "cloudwatch.tf").read_text()
        assert "aws_cloudwatch_log_group" in content
        assert "retention_in_days" in content

    def test_backend_tf_no_bucket(self, config, tmp_path):
        generate_terraform(config, tmp_path)
        content = (tmp_path / "backend.tf").read_text()
        assert "No remote backend configured" in content

    def test_backend_tf_with_bucket(self, tmp_path):
        config = TerraformConfig(
            workflow_name="my-wf",
            backend_bucket="my-tf-state",
            backend_key="rsf/my-wf/state.tfstate",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "backend.tf").read_text()
        assert 'backend "s3"' in content
        assert "my-tf-state" in content
        assert "rsf/my-wf/state.tfstate" in content

    def test_backend_tf_with_dynamodb(self, tmp_path):
        config = TerraformConfig(
            workflow_name="my-wf",
            backend_bucket="my-bucket",
            backend_dynamodb_table="my-lock-table",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "backend.tf").read_text()
        assert "my-lock-table" in content

    def test_no_raw_terraform_interpolation_conflict(self, config, tmp_path):
        """Generated HCL must not have conflicting ${}."""
        generate_terraform(config, tmp_path)
        for tf_file in tmp_path.glob("*.tf"):
            content = tf_file.read_text()
            # ${var.x} and ${path.x} and ${local.x} are legitimate Terraform
            # What we must NOT have is raw Jinja2 << >> or <% %>
            assert "<<" not in content, f"Raw << found in {tf_file.name}"
            assert ">>" not in content, f"Raw >> found in {tf_file.name}"

    def test_resource_id_is_valid_terraform_identifier(self, tmp_path):
        """Resource IDs derived from workflow names are valid Terraform identifiers."""
        import re

        test_cases = [
            ("my-workflow", "my_workflow"),
            ("MyWorkflow", "my_workflow"),
            ("ProcessOrderV2", "process_order_v2"),
            ("simple", "simple"),
        ]
        for workflow_name, expected_id in test_cases:
            config = TerraformConfig(workflow_name=workflow_name)
            result_dir = tmp_path / workflow_name
            generate_terraform(config, result_dir)
            content = (result_dir / "main.tf").read_text()
            assert f'resource "aws_lambda_function" "{expected_id}"' in content


class TestGenerationGap:
    def test_user_file_not_overwritten(self, tmp_path):
        """User-modified Terraform files are preserved."""
        config = TerraformConfig(workflow_name="test")

        # Create a user-modified main.tf
        (tmp_path / "main.tf").write_text("# My custom main.tf\nresource ...\n")

        result = generate_terraform(config, tmp_path)
        assert tmp_path / "main.tf" in result.skipped_files
        assert "My custom main.tf" in (tmp_path / "main.tf").read_text()

    def test_generated_file_overwritten(self, tmp_path):
        """Generated files (with marker) are always overwritten."""
        config = TerraformConfig(workflow_name="test")

        # First generation
        generate_terraform(config, tmp_path)

        # Verify marker present
        content = (tmp_path / "main.tf").read_text()
        assert content.startswith(GENERATED_MARKER)

        # Second generation should still overwrite
        result = generate_terraform(config, tmp_path)
        assert tmp_path / "main.tf" in result.generated_files

    def test_mixed_files(self, tmp_path):
        """Some files user-modified, some generated — only generated overwritten."""
        config = TerraformConfig(workflow_name="test")

        # First generation
        generate_terraform(config, tmp_path)

        # User modifies variables.tf
        (tmp_path / "variables.tf").write_text("# My custom variables\n")

        # Second generation
        result = generate_terraform(config, tmp_path)

        # variables.tf should be skipped
        assert tmp_path / "variables.tf" in result.skipped_files
        assert "My custom variables" in (tmp_path / "variables.tf").read_text()

        # Other files should be regenerated
        assert tmp_path / "main.tf" in result.generated_files

    def test_replay_safety(self, tmp_path):
        """Running generation twice produces identical output."""
        config = TerraformConfig(workflow_name="test", aws_region="us-east-2")

        generate_terraform(config, tmp_path)
        first_run = {}
        for f in tmp_path.glob("*.tf"):
            first_run[f.name] = f.read_text()

        generate_terraform(config, tmp_path)
        second_run = {}
        for f in tmp_path.glob("*.tf"):
            second_run[f.name] = f.read_text()

        assert first_run == second_run
