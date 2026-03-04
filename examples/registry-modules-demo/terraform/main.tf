# Lambda Durable Function + alias deployed via terraform-aws-modules/lambda/aws v8.7.0
#
# IAM approach: hybrid
#   - Managed policy AWSLambdaBasicDurableExecutionRolePolicy (checked available in us-east-2)
#     covers: CheckpointDurableExecution, GetDurableExecutionState, CW Logs
#   - Inline supplement covers: InvokeFunction (self-invoke), ListDurableExecutionsByFunction,
#     GetDurableExecution (describe API, distinct from GetDurableExecutionState replay API)
#
# See iam_durable.tf for the policy split rationale.

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.7.0"

  function_name = var.workflow_name
  handler       = "generated.orchestrator.lambda_handler"
  runtime       = "python3.13"

  # Pre-built zip — deploy.sh creates build/function.zip before calling terraform apply.
  # ignore_source_code_hash prevents re-deploy on every apply when the zip is rebuilt
  # outside Terraform's control.
  create_package          = false
  local_existing_package  = "${path.module}/../build/function.zip"
  ignore_source_code_hash = true

  # Durable Functions configuration.
  # CRITICAL: durable_config block is gated on durable_config_execution_timeout != null.
  # coalesce() prevents null propagation from WorkflowMetadata (default is null in RSF).
  durable_config_execution_timeout = coalesce(var.execution_timeout, 86400)
  durable_config_retention_period  = 14

  # IAM role — created by the module.
  create_role                   = true
  attach_cloudwatch_logs_policy = true

  # Managed policy attachment (hybrid approach).
  # WARNING: attach_policies AND number_of_policies are both required.
  # Setting only policies = [...] silently attaches nothing.
  attach_policies    = true
  number_of_policies = 1
  policies = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy"
  ]

  # Inline supplement for actions not covered by the managed policy.
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DurableExtraPermissions"
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction",
        "lambda:ListDurableExecutionsByFunction",
        "lambda:GetDurableExecution"
      ]
      Resource = "*"
    }]
  })

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

# Lambda alias "live" — mandatory workaround for Terraform provider issue #45800.
# AllowInvokeLatest (AWS SDK for Go v2) is unresolved as of Jan 7, 2026.
# Always invoke durable functions via alias ARN, never $LATEST or unqualified ARN.
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = module.lambda.lambda_function_name
  function_version = module.lambda.lambda_function_version
}
