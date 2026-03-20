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

# --- SF Handler Lambda (ProcessCSV) ---

data "archive_file" "sf_handler_zip" {
  type        = "zip"
  source_dir  = local.handlers_dir
  output_path = "${path.module}/sf_handler.zip"
}

resource "aws_lambda_function" "sf_csv" {
  function_name    = "${var.name_prefix}-sf-csv"
  handler          = "choice_routing.sf_handler.csv_handler"
  runtime          = "python3.13"
  role             = var.lambda_role_arn
  filename         = data.archive_file.sf_handler_zip.output_path
  source_code_hash = data.archive_file.sf_handler_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      PARITY_S3_BUCKET = var.s3_bucket_name
    }
  }

}

# --- SF Handler Lambda (ProcessJSON) ---

resource "aws_lambda_function" "sf_json" {
  function_name    = "${var.name_prefix}-sf-json"
  handler          = "choice_routing.sf_handler.json_handler"
  runtime          = "python3.13"
  role             = var.lambda_role_arn
  filename         = data.archive_file.sf_handler_zip.output_path
  source_code_hash = data.archive_file.sf_handler_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      PARITY_S3_BUCKET = var.s3_bucket_name
    }
  }

}

# --- Step Functions State Machine ---

resource "aws_sfn_state_machine" "choice_routing" {
  name     = "${var.name_prefix}-sf"
  role_arn = var.sfn_role_arn

  definition = templatefile("${path.module}/sfn_definition.json", {
    s3_bucket      = var.s3_bucket_name
    csv_lambda_arn = aws_lambda_function.sf_csv.arn
    json_lambda_arn = aws_lambda_function.sf_json.arn
  })
}

# --- RSF Durable Lambda ---

data "archive_file" "rsf_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/rsf_choice.zip"
}

resource "aws_lambda_function" "rsf_choice" {
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
      PARITY_S3_BUCKET = var.s3_bucket_name
    }
  }

}

resource "aws_lambda_alias" "rsf_live" {
  name             = "live"
  function_name    = aws_lambda_function.rsf_choice.function_name
  function_version = "$LATEST"
}

resource "aws_cloudwatch_log_group" "rsf_logs" {
  name              = "/aws/lambda/${aws_lambda_function.rsf_choice.function_name}"
  retention_in_days = 1
}
