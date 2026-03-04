# RSF Feature: DynamoDB table persistence
# Registry module: terraform-aws-modules/dynamodb-table/aws v5.5.0
#
# Creates one DynamoDB table per entry in var.dynamodb_tables using for_each.
# The list-to-map conversion (for t in var.dynamodb_tables : t.table_name => t)
# keys each module instance by table_name, which appears in the Terraform state
# as module.dynamodb_table["my-table"].dynamodb_table_arn — readable and stable.
#
# RSF WorkflowMetadata field: dynamodb_tables (list[dict])
#   Each dict: table_name, partition_key {name, type}, billing_mode

module "dynamodb_table" {
  source   = "terraform-aws-modules/dynamodb-table/aws"
  version  = "5.5.0"
  for_each = { for t in var.dynamodb_tables : t.table_name => t }

  name         = each.value.table_name
  hash_key     = each.value.partition_key.name
  billing_mode = each.value.billing_mode

  attributes = [
    {
      name = each.value.partition_key.name
      type = each.value.partition_key.type
    }
  ]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
