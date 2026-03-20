variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "rsf-parity"
}
