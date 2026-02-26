# DynamoDB table for order-processing example — stores order history

resource "aws_dynamodb_table" "order_history" {
  name         = "${local.function_name}-order-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "orderId"

  attribute {
    name = "orderId"
    type = "S"
  }

  tags = {
    Project = "rsf-examples"
    Example = "order-processing"
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
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.order_history.arn
      }
    ]
  })
}

output "dynamodb_table_name" {
  description = "Name of the order history DynamoDB table"
  value       = aws_dynamodb_table.order_history.name
}
