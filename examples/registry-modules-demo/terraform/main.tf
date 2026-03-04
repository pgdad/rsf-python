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

  # Dead-letter queue wiring. Conditional on dlq_enabled — when false, Terraform omits the
  # attribute entirely (null is the module's default). Requires sqs.tf module to be applied first.
  dead_letter_target_arn = var.dlq_enabled ? module.sqs_dlq[0].queue_arn : null

  # Inline supplement for actions not covered by the managed policy.
  # Uses concat() to build the Statement list from conditional arrays.
  # IMPORTANT: empty list [] is used for false branches, NEVER null —
  # concat() accepts lists but not null (would cause a type error at plan time).
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [{
        Sid    = "DurableExtraPermissions"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:ListDurableExecutionsByFunction",
          "lambda:GetDurableExecution"
        ]
        Resource = "*"
      }],
      length(var.dynamodb_tables) > 0 ? [{
        Sid    = "DynamoDBTableAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [for t in module.dynamodb_table : t.dynamodb_table_arn]
      }] : [],
      var.dlq_enabled ? [{
        Sid      = "SQSDLQAccess"
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = [module.sqs_dlq[0].queue_arn]
      }] : []
    )
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
