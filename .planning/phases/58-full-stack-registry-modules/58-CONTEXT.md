# Phase 58: Full-Stack Registry Modules - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the registry-modules-demo example with DynamoDB table, SQS DLQ, CloudWatch alarms, and SNS topic — each deployed via the corresponding terraform-aws-modules registry module. Phase 57 delivered the Lambda + IAM Terraform. Phase 58 adds the remaining four resource types. No workflow YAML or handler changes — only new Terraform files, updated deploy.sh, and updated variables/outputs.

</domain>

<decisions>
## Implementation Decisions

### Metadata passing strategy
- Migrate deploy.sh from scalar `-var` flags to a generated `terraform.tfvars.json` file
- deploy.sh uses jq to transform RSF_METADATA_FILE into terraform.tfvars.json with all variables (workflow_name, execution_timeout, dynamodb_tables, dlq_enabled, dlq_queue_name, dlq_max_receive_count, alarms)
- `terraform apply -var-file=terraform.tfvars.json` replaces individual `-var` flags
- terraform.tfvars.json is gitignored (generated at deploy time, contains runtime values)
- Same approach for `terraform destroy -var-file=terraform.tfvars.json`
- This handles list/object variables cleanly and is tutorial-friendly (readers can inspect the generated file)

### Alarm definitions
- Add alarms section to workflow.yaml with all three alarm types: error_rate, duration, throttle
- Use reasonable tutorial-friendly thresholds (not production-tuned — this is a learning example)
- All alarms auto-create an SNS topic via the sns registry module (no pre-existing sns_topic_arn)

### Terraform file layout
- One .tf file per registry module: `dynamodb.tf`, `sqs.tf`, `alarms.tf`, `sns.tf`
- Each file is self-contained with its registry module block
- Matches tutorial structure: one section per resource type, easy to follow

### DynamoDB Terraform
- Use terraform-aws-modules/dynamodb-table/aws v5.5.0
- `for_each` over dynamodb_tables variable (list of objects → map keyed by table_name)
- Map RSF table schema (table_name, partition_key, billing_mode) to module inputs
- Add DynamoDB IAM permissions to Lambda role (read/write on created table ARNs)

### SQS DLQ Terraform
- Use terraform-aws-modules/sqs/aws v5.2.1
- Conditional creation: `count = var.dlq_enabled ? 1 : 0`
- Wire to lambda module via `dead_letter_target_arn` — requires updating main.tf lambda module block
- Pass max_receive_count from metadata
- 14-day message retention (matches RSF's existing DLQ template)

### CloudWatch alarms Terraform
- Use terraform-aws-modules/cloudwatch/aws v5.7.2 `//modules/metric-alarm` submodule
- One module block per alarm type (error_rate, duration, throttle)
- Dynamic creation from alarms variable (list of alarm configs)
- All alarms reference the Lambda function name from module.lambda output
- All alarms send to SNS topic created by sns module

### SNS topic Terraform
- Use terraform-aws-modules/sns/aws v7.1.0
- Single topic for all alarm notifications
- Created unconditionally when alarms exist (alarms require a notification target)
- Topic ARN passed to alarm modules via `alarm_actions`

### IAM expansion
- Extend the inline supplement policy in main.tf to include DynamoDB and SQS permissions
- DynamoDB: dynamodb:PutItem, dynamodb:GetItem, dynamodb:UpdateItem, dynamodb:DeleteItem, dynamodb:Query, dynamodb:Scan — scoped to created table ARNs
- SQS: sqs:SendMessage — scoped to DLQ ARN (conditional on dlq_enabled)
- Use conditional jsonencode to build policy statement list dynamically

### Claude's Discretion
- Exact alarm thresholds and evaluation periods for the tutorial example
- Whether to use `for_each` with `tomap()` or `for` expression for DynamoDB module iteration
- How to structure the conditional IAM policy (single policy_json with conditional statements vs. separate attach_policy_jsons)
- Exact terraform.tfvars.json generation jq command structure
- Whether alarms variable uses a single list or separate per-type variables
- Output additions (DynamoDB table names, SQS queue URL, SNS topic ARN, alarm names)
- Whether to add alarm config to workflow.yaml in this phase or defer to a separate small update

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `examples/registry-modules-demo/terraform/main.tf`: Lambda module block with inline IAM — extend policy_json for DynamoDB/SQS permissions
- `examples/registry-modules-demo/terraform/versions.tf`: All five registry module versions already pinned
- `examples/registry-modules-demo/deploy.sh`: Working jq + `-var` pattern — refactor to tfvars.json generation
- `src/rsf/terraform/templates/dynamodb.tf.j2`: RSF's raw HCL DynamoDB template — reference for field mapping
- `src/rsf/terraform/templates/dlq.tf.j2`: RSF's raw SQS DLQ template — reference for field mapping
- `src/rsf/terraform/templates/alarms.tf.j2`: RSF's raw CloudWatch alarm template with SNS — reference for metric names, dimensions, treat_missing_data
- `src/rsf/providers/metadata.py`: WorkflowMetadata with dynamodb_tables, alarms, dlq_enabled, dlq_max_receive_count, dlq_queue_name fields

### Established Patterns
- FileTransport (RSF_METADATA_FILE) provides all metadata as JSON — deploy.sh reads this
- Phase 57 deploy.sh: jq extraction → -var flags → terraform apply; Phase 58 evolves to jq → tfvars.json → -var-file
- Hybrid IAM: managed policy via module + inline supplement via policy_json
- Module versions as exact strings (not ~> ranges)
- `create_package = false` + `local_existing_package` for Lambda zip
- `workflow.yaml` declares infrastructure (DynamoDB tables, DLQ) — Terraform reads from metadata

### Integration Points
- `examples/registry-modules-demo/terraform/main.tf` — lambda module needs dead_letter_target_arn added
- `examples/registry-modules-demo/terraform/variables.tf` — new variables for dynamodb_tables, dlq config, alarms
- `examples/registry-modules-demo/terraform/outputs.tf` — new outputs for DynamoDB, SQS, SNS, CloudWatch
- `examples/registry-modules-demo/deploy.sh` — refactor metadata extraction to generate tfvars.json
- `examples/registry-modules-demo/workflow.yaml` — add alarms section (if not deferred)

</code_context>

<specifics>
## Specific Ideas

- deploy.sh should generate terraform.tfvars.json so tutorial readers can inspect the generated file and understand what RSF metadata maps to which Terraform variables
- The alarm thresholds should be clearly documented in workflow.yaml comments explaining what each alarm monitors
- Each new .tf file should have a header comment explaining which RSF feature it maps and which registry module it uses — tutorial readers will reference these files

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 58-full-stack-registry-modules*
*Context gathered: 2026-03-04*
