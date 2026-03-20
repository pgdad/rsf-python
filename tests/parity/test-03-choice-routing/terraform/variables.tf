variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "name_prefix" {
  type    = string
  default = "rsf-parity-choice"
}

variable "s3_bucket_name" {
  description = "Shared S3 bucket name"
  type        = string
}

variable "lambda_role_arn" {
  description = "Shared IAM role ARN for Lambda"
  type        = string
}

variable "sfn_role_arn" {
  description = "Shared IAM role ARN for Step Functions"
  type        = string
}
