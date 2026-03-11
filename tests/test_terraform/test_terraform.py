"""Tests for Terraform generation."""

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
        assert "ManagedBy" in content

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
        assert "ManagedBy" in content

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


class TestTriggerGeneration:
    """Tests for event trigger Terraform generation."""

    def test_eventbridge_trigger_creates_resources(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[
                {
                    "type": "eventbridge",
                    "schedule_expression": "rate(5 minutes)",
                    "event_pattern": None,
                }
            ],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_cloudwatch_event_rule" in content
        assert "aws_cloudwatch_event_target" in content
        assert "rate(5 minutes)" in content

    def test_sqs_trigger_creates_resources(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[{"type": "sqs", "queue_name": "order-events", "batch_size": 5}],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_sqs_queue" in content
        assert "aws_lambda_event_source_mapping" in content
        assert "order-events" in content

    def test_sns_trigger_creates_resources(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[
                {
                    "type": "sns",
                    "topic_arn": "arn:aws:sns:us-east-1:123456789012:MyTopic",
                }
            ],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_sns_topic_subscription" in content
        assert "aws_lambda_permission" in content
        assert "arn:aws:sns:us-east-1:123456789012:MyTopic" in content

    def test_multiple_triggers_all_present(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[
                {"type": "eventbridge", "schedule_expression": "rate(1 hour)", "event_pattern": None},
                {"type": "sqs", "queue_name": "orders", "batch_size": 10},
                {"type": "sns", "topic_arn": "arn:aws:sns:us-east-1:123456789012:T"},
            ],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_cloudwatch_event_rule" in content
        assert "aws_sqs_queue" in content
        assert "aws_sns_topic_subscription" in content

    def test_no_triggers_no_triggers_tf(self, tmp_path):
        config = TerraformConfig(workflow_name="test")
        result = generate_terraform(config, tmp_path)
        assert not (tmp_path / "triggers.tf").exists()
        assert len(result.generated_files) == 6  # standard files only

    def test_sqs_trigger_produces_iam_permissions(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[{"type": "sqs", "queue_name": "my-queue", "batch_size": 10}],
            has_sqs_triggers=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "SQSTriggerAccess" in content
        assert "sqs:ReceiveMessage" in content
        assert "sqs:DeleteMessage" in content
        assert "sqs:GetQueueAttributes" in content

    def test_eventbridge_trigger_produces_lambda_permission(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            triggers=[{"type": "eventbridge", "schedule_expression": "rate(5 minutes)", "event_pattern": None}],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_lambda_permission" in content
        assert "events.amazonaws.com" in content


class TestDynamoDBGeneration:
    """Tests for DynamoDB Terraform generation."""

    def test_dynamodb_table_creates_resource(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "order_id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "aws_dynamodb_table" in content
        assert "orders" in content

    def test_dynamodb_table_with_sort_key(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "order_id", "type": "S"},
                    "sort_key": {"name": "created_at", "type": "N"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "hash_key" in content
        assert "range_key" in content
        assert "order_id" in content
        assert "created_at" in content

    def test_dynamodb_provisioned_billing(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PROVISIONED",
                    "read_capacity": 5,
                    "write_capacity": 10,
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "PROVISIONED" in content
        assert "read_capacity" in content
        assert "write_capacity" in content

    def test_dynamodb_pay_per_request_no_capacity(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "PAY_PER_REQUEST" in content
        # PAY_PER_REQUEST should NOT have read/write capacity
        assert "read_capacity" not in content
        assert "write_capacity" not in content

    def test_multiple_dynamodb_tables(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "order_id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                },
                {
                    "table_name": "inventory",
                    "partition_key": {"name": "product_id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                },
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "orders" in content
        assert "inventory" in content

    def test_no_dynamodb_no_dynamodb_tf(self, tmp_path):
        config = TerraformConfig(workflow_name="test")
        result = generate_terraform(config, tmp_path)
        assert not (tmp_path / "dynamodb.tf").exists()
        assert len(result.generated_files) == 6  # standard files only

    def test_dynamodb_produces_iam_permissions(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "DynamoDBAccess" in content
        assert "dynamodb:GetItem" in content
        assert "dynamodb:PutItem" in content
        assert "dynamodb:UpdateItem" in content
        assert "dynamodb:DeleteItem" in content
        assert "dynamodb:Query" in content
        assert "dynamodb:Scan" in content

    def test_dynamodb_iam_includes_batch_operations(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "dynamodb:BatchGetItem" in content
        assert "dynamodb:BatchWriteItem" in content


class TestLambdaUrlTerraform:
    """Tests for Lambda Function URL Terraform generation."""

    def test_lambda_url_none_auth_generates_resource(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="NONE",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "lambda_url.tf").read_text()
        assert "aws_lambda_function_url" in content
        assert 'authorization_type = "NONE"' in content

    def test_lambda_url_aws_iam_auth_generates_resource(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="AWS_IAM",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "lambda_url.tf").read_text()
        assert 'authorization_type = "AWS_IAM"' in content

    def test_lambda_url_enabled_adds_function_url_output(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="NONE",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "outputs.tf").read_text()
        assert "function_url" in content
        assert "aws_lambda_function_url" in content

    def test_lambda_url_aws_iam_adds_invoke_iam_statement(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="AWS_IAM",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert content.count("Sid") == 4
        assert "InvokeFunctionUrl" in content
        assert "lambda:InvokeFunctionUrl" in content

    def test_lambda_url_none_auth_no_extra_iam(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="NONE",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert content.count("Sid") == 3
        assert "InvokeFunctionUrl" not in content

    def test_lambda_url_disabled_no_extra_files(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=False,
        )
        result = generate_terraform(config, tmp_path)
        assert len(result.generated_files) == 6
        assert not (tmp_path / "lambda_url.tf").exists()

    def test_lambda_url_default_no_extra_files(self, tmp_path):
        config = TerraformConfig(workflow_name="test")
        result = generate_terraform(config, tmp_path)
        assert len(result.generated_files) == 6
        assert not (tmp_path / "lambda_url.tf").exists()

    def test_lambda_url_no_raw_jinja_delimiters(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            lambda_url_enabled=True,
            lambda_url_auth_type="AWS_IAM",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "lambda_url.tf").read_text()
        assert "<<" not in content
        assert ">>" not in content
        assert "<%" not in content
        assert "%>" not in content


class TestAlarmGeneration:
    """Tests for CloudWatch alarm Terraform generation."""

    def test_error_rate_alarm_creates_cloudwatch_alarm(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 2,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert "aws_cloudwatch_metric_alarm" in content
        assert '"Errors"' in content
        assert '"Sum"' in content
        assert "aws_sns_topic" in content  # auto-generated SNS topic

    def test_duration_alarm_creates_cloudwatch_alarm(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {
                    "type": "duration",
                    "threshold": 5000,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert "aws_cloudwatch_metric_alarm" in content
        assert '"Duration"' in content
        assert '"Average"' in content

    def test_throttle_alarm_creates_cloudwatch_alarm(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {
                    "type": "throttle",
                    "threshold": 10,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert "aws_cloudwatch_metric_alarm" in content
        assert '"Throttles"' in content
        assert '"Sum"' in content

    def test_alarm_with_existing_sns_topic_no_auto_topic(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": "arn:aws:sns:us-east-2:123456789012:MyAlerts",
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert "aws_cloudwatch_metric_alarm" in content
        assert "arn:aws:sns:us-east-2:123456789012:MyAlerts" in content
        # Should NOT create an auto-generated SNS topic
        assert 'resource "aws_sns_topic"' not in content

    def test_alarm_without_sns_topic_creates_auto_topic(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert 'resource "aws_sns_topic"' in content
        assert "alarm_notifications" in content

    def test_multiple_alarms_all_generated(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {"type": "error_rate", "threshold": 5, "period": 300, "evaluation_periods": 1, "sns_topic_arn": None},
                {"type": "duration", "threshold": 10000, "period": 60, "evaluation_periods": 1, "sns_topic_arn": None},
                {"type": "throttle", "threshold": 10, "period": 300, "evaluation_periods": 1, "sns_topic_arn": None},
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        assert '"Errors"' in content
        assert '"Duration"' in content
        assert '"Throttles"' in content

    def test_no_alarms_no_alarms_tf(self, tmp_path):
        config = TerraformConfig(workflow_name="test")
        result = generate_terraform(config, tmp_path)
        assert not (tmp_path / "alarms.tf").exists()
        assert len(result.generated_files) == 6  # standard files only

    def test_alarms_produce_sns_iam_permission(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            alarms=[
                {"type": "error_rate", "threshold": 5, "period": 300, "evaluation_periods": 1, "sns_topic_arn": None},
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "SNSAlarmPublish" in content
        assert "sns:Publish" in content


class TestDLQGeneration:
    """Tests for dead letter queue Terraform generation."""

    def test_dlq_enabled_creates_sqs_queue(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dlq.tf").read_text()
        assert "aws_sqs_queue" in content
        assert "dlq" in content

    def test_dlq_default_queue_name(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dlq.tf").read_text()
        assert "${local.function_name}-dlq" in content

    def test_dlq_custom_queue_name(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
            dlq_queue_name="my-custom-dlq",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dlq.tf").read_text()
        assert "my-custom-dlq" in content

    def test_dlq_creates_dead_letter_config_in_main(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "main.tf").read_text()
        assert "dead_letter_config" in content
        assert "_dlq.arn" in content

    def test_no_dlq_no_dlq_tf(self, tmp_path):
        config = TerraformConfig(workflow_name="test")
        generate_terraform(config, tmp_path)
        assert not (tmp_path / "dlq.tf").exists()
        content = (tmp_path / "main.tf").read_text()
        assert "dead_letter_config" not in content

    def test_dlq_disabled_no_dlq_tf(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=False,
        )
        generate_terraform(config, tmp_path)
        assert not (tmp_path / "dlq.tf").exists()

    def test_dlq_produces_sqs_iam_permission(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "DLQSendMessage" in content
        assert "sqs:SendMessage" in content

    def test_dlq_message_retention(self, tmp_path):
        config = TerraformConfig(
            workflow_name="test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dlq.tf").read_text()
        assert "message_retention_seconds" in content
        assert "1209600" in content  # 14 days


class TestStageConfig:
    """Tests for stage-aware Terraform generation."""

    def test_stage_produces_stage_variable(self, tmp_path):
        """generate_terraform with stage produces variables.tf with stage variable."""
        config = TerraformConfig(
            workflow_name="test",
            stage="prod",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "variables.tf").read_text()
        assert 'variable "stage"' in content
        assert '"prod"' in content

    def test_no_stage_no_stage_variable(self, tmp_path):
        """generate_terraform without stage produces variables.tf without stage variable (backward compatible)."""
        config = TerraformConfig(
            workflow_name="test",
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "variables.tf").read_text()
        assert 'variable "stage"' not in content

    def test_stage_config_field_default_none(self):
        """TerraformConfig.stage defaults to None."""
        config = TerraformConfig(workflow_name="test")
        assert config.stage is None


class TestTagGeneration:
    """Tests verifying ManagedBy/Workflow tags are present on all taggable resources."""

    def test_main_tf_has_managed_by_tag(self, tmp_path):
        """Generated main.tf includes ManagedBy=rsf tag on aws_lambda_function."""
        config = TerraformConfig(workflow_name="tag-test")
        generate_terraform(config, tmp_path)
        content = (tmp_path / "main.tf").read_text()
        assert "ManagedBy" in content
        assert '"rsf"' in content

    def test_iam_role_has_tags(self, tmp_path):
        """Generated iam.tf includes tags on aws_iam_role (not aws_iam_role_policy)."""
        config = TerraformConfig(workflow_name="tag-test")
        generate_terraform(config, tmp_path)
        content = (tmp_path / "iam.tf").read_text()
        assert "ManagedBy" in content
        # tags block appears before aws_iam_role_policy resource (on the role)
        role_end = content.index('resource "aws_iam_role_policy"')
        role_section = content[:role_end]
        assert "ManagedBy" in role_section

    def test_cloudwatch_log_group_has_tags(self, tmp_path):
        """Generated cloudwatch.tf includes tags on aws_cloudwatch_log_group."""
        config = TerraformConfig(workflow_name="tag-test")
        generate_terraform(config, tmp_path)
        content = (tmp_path / "cloudwatch.tf").read_text()
        assert "ManagedBy" in content
        assert '"rsf"' in content

    def test_dynamodb_tables_have_tags(self, tmp_path):
        """Generated dynamodb.tf includes tags on each aws_dynamodb_table."""
        config = TerraformConfig(
            workflow_name="tag-test",
            dynamodb_tables=[
                {
                    "table_name": "orders",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                },
                {
                    "table_name": "events",
                    "partition_key": {"name": "event_id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                },
            ],
            has_dynamodb_tables=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dynamodb.tf").read_text()
        assert "ManagedBy" in content
        # Two tables — tags should appear twice
        assert content.count("ManagedBy") == 2

    def test_dlq_has_tags(self, tmp_path):
        """Generated dlq.tf includes tags on aws_sqs_queue."""
        config = TerraformConfig(
            workflow_name="tag-test",
            dlq_enabled=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "dlq.tf").read_text()
        assert "ManagedBy" in content
        assert '"rsf"' in content

    def test_alarm_sns_topic_has_tags(self, tmp_path):
        """Generated alarms.tf includes tags on auto-created aws_sns_topic."""
        config = TerraformConfig(
            workflow_name="tag-test",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        # SNS topic is created when sns_topic_arn is None
        assert 'resource "aws_sns_topic"' in content
        # Verify tags appear on the SNS topic (before the alarm resource)
        sns_topic_end = content.index('resource "aws_cloudwatch_metric_alarm"')
        sns_section = content[:sns_topic_end]
        assert "ManagedBy" in sns_section

    def test_alarm_resources_have_tags(self, tmp_path):
        """Generated alarms.tf includes tags on aws_cloudwatch_metric_alarm resources."""
        config = TerraformConfig(
            workflow_name="tag-test",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                },
                {
                    "type": "duration",
                    "threshold": 10000,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                },
                {
                    "type": "throttle",
                    "threshold": 10,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                },
            ],
            has_alarms=True,
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "alarms.tf").read_text()
        # 1 SNS topic + 3 alarms = 4 ManagedBy occurrences
        assert content.count("ManagedBy") == 4

    def test_sqs_trigger_queue_has_tags(self, tmp_path):
        """Generated triggers.tf includes tags on aws_sqs_queue for SQS trigger."""
        config = TerraformConfig(
            workflow_name="tag-test",
            triggers=[{"type": "sqs", "queue_name": "my-queue", "batch_size": 5}],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_sqs_queue" in content
        assert "ManagedBy" in content

    def test_eventbridge_rule_has_tags(self, tmp_path):
        """Generated triggers.tf includes tags on aws_cloudwatch_event_rule."""
        config = TerraformConfig(
            workflow_name="tag-test",
            triggers=[
                {
                    "type": "eventbridge",
                    "schedule_expression": "rate(5 minutes)",
                    "event_pattern": None,
                }
            ],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        assert "aws_cloudwatch_event_rule" in content
        assert "ManagedBy" in content

    def test_lambda_permission_and_event_target_have_no_tags(self, tmp_path):
        """Non-taggable resources (aws_lambda_permission, aws_cloudwatch_event_target) must not have tags."""
        config = TerraformConfig(
            workflow_name="tag-test",
            triggers=[
                {
                    "type": "eventbridge",
                    "schedule_expression": "rate(1 hour)",
                    "event_pattern": None,
                }
            ],
        )
        generate_terraform(config, tmp_path)
        content = (tmp_path / "triggers.tf").read_text()
        # tags should only appear inside the event_rule block, not the permission or target blocks
        # The event_rule block ends before aws_cloudwatch_event_target
        event_target_start = content.index('resource "aws_cloudwatch_event_target"')
        after_event_target = content[event_target_start:]
        # No tags after the event_target (lambda_permission follows it)
        assert "ManagedBy" not in after_event_target

    def test_all_generated_files_have_tags(self, tmp_path):
        """Full generation with all features: every file creating taggable resources has ManagedBy."""
        config = TerraformConfig(
            workflow_name="full-test",
            dlq_enabled=True,
            lambda_url_enabled=True,
            lambda_url_auth_type="NONE",
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            has_alarms=True,
            dynamodb_tables=[
                {
                    "table_name": "records",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            has_dynamodb_tables=True,
            triggers=[{"type": "sqs", "queue_name": "events-queue", "batch_size": 1}],
        )
        generate_terraform(config, tmp_path)

        # These files contain taggable resources and MUST have ManagedBy
        taggable_files = ["main.tf", "iam.tf", "cloudwatch.tf", "dynamodb.tf", "dlq.tf", "alarms.tf", "triggers.tf"]
        for filename in taggable_files:
            content = (tmp_path / filename).read_text()
            assert "ManagedBy" in content, f"Expected ManagedBy tag in {filename}"

        # lambda_url.tf must NOT have tags (aws_lambda_function_url is not taggable)
        lambda_url_content = (tmp_path / "lambda_url.tf").read_text()
        assert "ManagedBy" not in lambda_url_content, "lambda_url.tf should not have tags"

    def test_workflow_tag_value_uses_var_workflow_name(self, tmp_path):
        """Tags use var.workflow_name (Terraform variable) not a hardcoded string."""
        config = TerraformConfig(workflow_name="my-workflow")
        generate_terraform(config, tmp_path)
        for filename in ["main.tf", "iam.tf", "cloudwatch.tf"]:
            content = (tmp_path / filename).read_text()
            assert "var.workflow_name" in content, f"Expected var.workflow_name in {filename}"
