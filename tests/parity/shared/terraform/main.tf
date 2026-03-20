terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  bucket_name = "${var.name_prefix}-${random_id.suffix.hex}"
  queue_name  = "${var.name_prefix}-queue-${random_id.suffix.hex}"
  dlq_name    = "${var.name_prefix}-dlq-${random_id.suffix.hex}"
}

# --- S3 Bucket ---

resource "aws_s3_bucket" "parity" {
  bucket        = local.bucket_name
  force_destroy = true

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

resource "aws_s3_bucket_versioning" "parity" {
  bucket = aws_s3_bucket.parity.id
  versioning_configuration {
    status = "Enabled"
  }
}

# --- SQS Queues ---

resource "aws_sqs_queue" "dlq" {
  name                      = local.dlq_name
  message_retention_seconds = 300

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

resource "aws_sqs_queue" "parity" {
  name                       = local.queue_name
  visibility_timeout_seconds = 30
  message_retention_seconds  = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

# --- IAM Role for Lambda Handlers ---

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.name_prefix}-lambda-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }

  statement {
    sid = "S3Access"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.parity.arn}/*"]
  }

  statement {
    sid = "SQSAccess"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:DeleteMessageBatch",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.parity.arn]
  }

  statement {
    sid       = "LambdaSelfInvoke"
    actions   = ["lambda:InvokeFunction"]
    resources = ["*"]
  }

  statement {
    sid = "DurableExecution"
    actions = [
      "lambda:Checkpoint",
      "lambda:GetDurableExecution",
      "lambda:GetDurableExecutionState",
      "lambda:ListDurableExecutionsByFunction",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.name_prefix}-lambda-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# --- IAM Role for Step Functions ---

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn_role" {
  name               = "${var.name_prefix}-sfn-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

data "aws_iam_policy_document" "sfn_policy" {
  statement {
    sid = "InvokeLambda"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = ["*"]
  }

  statement {
    sid = "S3Access"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.parity.arn}/*"]
  }

  statement {
    sid = "SQSAccess"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:DeleteMessageBatch",
      "sqs:SendMessage",
    ]
    resources = [aws_sqs_queue.parity.arn]
  }

  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn_policy" {
  name   = "${var.name_prefix}-sfn-policy"
  role   = aws_iam_role.sfn_role.id
  policy = data.aws_iam_policy_document.sfn_policy.json
}
