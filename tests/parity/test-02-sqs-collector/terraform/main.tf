terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  handlers_dir = "${path.module}/../../handlers"
}

# --- SF Handler Lambda (AppendMessage) ---

data "archive_file" "sf_handler_zip" {
  type        = "zip"
  source_dir  = local.handlers_dir
  output_path = "${path.module}/sf_handler.zip"
}

resource "aws_lambda_function" "sf_append" {
  function_name    = "${var.name_prefix}-sf-append"
  handler          = "sqs_collector.sf_handler.append_handler"
  runtime          = "python3.13"
  role             = var.lambda_role_arn
  filename         = data.archive_file.sf_handler_zip.output_path
  source_code_hash = data.archive_file.sf_handler_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      PARITY_S3_BUCKET    = var.s3_bucket_name
      PARITY_SQS_QUEUE_URL = var.sqs_queue_url
    }
  }

}

# --- SF Handler Lambda (DeleteMessages) ---

resource "aws_lambda_function" "sf_delete" {
  function_name    = "${var.name_prefix}-sf-delete"
  handler          = "sqs_collector.sf_handler.delete_handler"
  runtime          = "python3.13"
  role             = var.lambda_role_arn
  filename         = data.archive_file.sf_handler_zip.output_path
  source_code_hash = data.archive_file.sf_handler_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      PARITY_S3_BUCKET    = var.s3_bucket_name
      PARITY_SQS_QUEUE_URL = var.sqs_queue_url
    }
  }

}

# --- Step Functions State Machine ---

resource "aws_sfn_state_machine" "sqs_collector" {
  name     = "${var.name_prefix}-sf"
  role_arn = var.sfn_role_arn

  definition = templatefile("${path.module}/sfn_definition.json", {
    sqs_queue_url      = var.sqs_queue_url
    s3_bucket          = var.s3_bucket_name
    append_lambda_arn  = aws_lambda_function.sf_append.arn
    output_key_prefix  = "parity/sqs-collector"
    delete_lambda_arn  = aws_lambda_function.sf_delete.arn
  })
}

# --- RSF Durable Lambda ---

data "archive_file" "rsf_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/rsf_sqs.zip"
}

resource "aws_lambda_function" "rsf_sqs" {
  function_name    = "${var.name_prefix}-rsf"
  handler          = "generated.orchestrator.lambda_handler"
  runtime          = "python3.13"
  role             = var.lambda_role_arn
  filename         = data.archive_file.rsf_zip.output_path
  source_code_hash = data.archive_file.rsf_zip.output_base64sha256
  timeout          = 900
  memory_size      = 256

  durable_config {
    execution_timeout = 600
    retention_period  = 1
  }

  logging_config {
    log_format = "JSON"
  }

  environment {
    variables = {
      PARITY_S3_BUCKET    = var.s3_bucket_name
      PARITY_SQS_QUEUE_URL = var.sqs_queue_url
    }
  }

}

resource "aws_lambda_alias" "rsf_live" {
  name             = "live"
  function_name    = aws_lambda_function.rsf_sqs.function_name
  function_version = "$LATEST"
}

resource "aws_cloudwatch_log_group" "rsf_logs" {
  name              = "/aws/lambda/${aws_lambda_function.rsf_sqs.function_name}"
  retention_in_days = 1
}
