variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-2"
}

variable "workflow_name" {
  description = "Workflow name — used as Lambda function name and resource name prefix"
  type        = string
  # No default — provided by deploy.sh from RSF_METADATA_FILE
}

variable "execution_timeout" {
  description = "Durable execution timeout in seconds (1 to 31622400)"
  type        = number
  default     = 86400

  validation {
    condition     = var.execution_timeout >= 1 && var.execution_timeout <= 31622400
    error_message = "execution_timeout must be between 1 and 31622400 seconds."
  }
}

# ─── DynamoDB ───────────────────────────────────────────────────────────────

variable "dynamodb_tables" {
  description = "DynamoDB tables to create for workflow state. Maps to RSF WorkflowMetadata.dynamodb_tables."
  type = list(object({
    table_name    = string
    partition_key = object({ name = string, type = string })
    billing_mode  = string
  }))
  default = []
}

# ─── SQS Dead-Letter Queue ──────────────────────────────────────────────────

variable "dlq_enabled" {
  description = "Whether to create a dead-letter queue for failed Lambda invocations. Maps to RSF WorkflowMetadata.dlq_enabled."
  type        = bool
  default     = false
}

variable "dlq_queue_name" {
  description = "SQS DLQ name. Defaults to '<workflow_name>-dlq' when null. Maps to RSF WorkflowMetadata.dlq_queue_name."
  type        = string
  default     = null
}

variable "dlq_max_receive_count" {
  description = "Number of times a message is delivered before being moved to the DLQ. Maps to RSF WorkflowMetadata.dlq_max_receive_count."
  type        = number
  default     = 3
}

# ─── CloudWatch Alarms ──────────────────────────────────────────────────────

variable "alarms" {
  description = "CloudWatch alarms to create. Supported types: error_rate, duration, throttle. Maps to RSF WorkflowMetadata.alarms."
  type = list(object({
    type               = string
    threshold          = number
    period             = number
    evaluation_periods = number
  }))
  default = []
}
