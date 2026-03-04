output "alias_arn" {
  description = "Invoke via alias ARN — never $LATEST (issue #45800)"
  value       = aws_lambda_alias.live.arn
}

output "function_name" {
  description = "Lambda function name"
  value       = module.lambda.lambda_function_name
}

output "role_arn" {
  description = "IAM role ARN"
  value       = module.lambda.lambda_role_arn
}

output "dynamodb_table_arns" {
  description = "Map of DynamoDB table name => table ARN for all tables created by this module"
  value       = { for k, v in module.dynamodb_table : k => v.dynamodb_table_arn }
}

output "sqs_dlq_url" {
  description = "SQS DLQ URL. Null when dlq_enabled = false."
  value       = var.dlq_enabled ? module.sqs_dlq[0].queue_url : null
}

output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications"
  value       = module.sns_alarms.topic_arn
}
