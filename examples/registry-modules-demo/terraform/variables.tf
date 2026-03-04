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
