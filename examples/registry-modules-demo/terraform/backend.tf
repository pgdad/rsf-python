# Backend configuration — local (Terraform default)
#
# No backend block is defined here. Terraform defaults to the local backend,
# storing state in terraform.tfstate in this directory.
#
# The local backend is intentional for this tutorial example:
#   - No S3 bucket or DynamoDB lock table setup required
#   - Tutorial readers can apply immediately without external infrastructure
#   - terraform.tfstate is gitignored (see ../.gitignore)
#
# For production use, replace the local backend with remote state:
#
#   terraform {
#     backend "s3" {
#       bucket         = "your-terraform-state-bucket"
#       key            = "registry-modules-demo/terraform.tfstate"
#       region         = "us-east-2"
#       dynamodb_table = "your-terraform-lock-table"
#       encrypt        = true
#     }
#   }
