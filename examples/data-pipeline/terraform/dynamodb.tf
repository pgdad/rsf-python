# DynamoDB table for data-pipeline example — stores ETL results

resource "aws_dynamodb_table" "pipeline_results" {
  name         = "${local.function_name}-pipeline-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Project = "rsf-examples"
    Example = "data-pipeline"
  }
}

resource "aws_iam_role_policy" "dynamodb_policy" {
  name = "${local.function_name}-dynamodb"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.pipeline_results.arn
      }
    ]
  })
}

output "dynamodb_table_name" {
  description = "Name of the pipeline results DynamoDB table"
  value       = aws_dynamodb_table.pipeline_results.name
}
