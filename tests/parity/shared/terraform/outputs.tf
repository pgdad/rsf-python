output "s3_bucket_name" {
  description = "S3 bucket for parity test data"
  value       = aws_s3_bucket.parity.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.parity.arn
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.parity.url
}

output "sqs_queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.parity.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda handlers"
  value       = aws_iam_role.lambda_role.arn
}

output "sfn_role_arn" {
  description = "IAM role ARN for Step Functions"
  value       = aws_iam_role.sfn_role.arn
}
