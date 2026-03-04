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
