# Tutorial 9: Custom Provider with Terraform Registry Modules

## What You'll Learn

In this tutorial you will:

- Configure RSF's custom provider system to use your own deploy script instead of RSF's built-in Terraform generation
- Write a `deploy.sh` script that bridges RSF's `WorkflowMetadata` to Terraform via `terraform.tfvars.json`
- Deploy a Lambda Durable Function using 5 community Terraform registry modules (Lambda, DynamoDB, SQS, SNS, CloudWatch)
- Understand the metadata transport pipeline: `workflow.yaml` → `WorkflowMetadata` → `RSF_METADATA_FILE` → `deploy.sh` → Terraform
- Compare raw HCL from RSF's TerraformProvider to the equivalent registry module configuration (Lambda and DynamoDB)
- Identify and avoid the 5 most common pitfalls when using custom providers with Terraform registry modules

---

## What You'll Build

An image-processing workflow deployed as a Lambda Durable Function backed by 5 Terraform registry modules:

1. **`terraform-aws-modules/lambda/aws` v8.7.0** — Lambda Durable Function + IAM role (hybrid managed + inline policy)
2. **`terraform-aws-modules/dynamodb-table/aws` v5.5.0** — `image-catalogue` table for persisting catalogue entries
3. **`terraform-aws-modules/sqs/aws` v5.2.1** — Dead-letter queue for failed Lambda invocations
4. **`terraform-aws-modules/cloudwatch/aws` v5.7.2** — Three CloudWatch metric alarms (error rate, duration, throttle)
5. **`terraform-aws-modules/sns/aws` v7.1.0** — SNS topic for alarm notifications

The workflow itself has 4 Task states: `ValidateImage` → `ResizeImage` → `AnalyzeContent` → `CatalogueImage`.

---

## Prerequisites

- Completed Tutorials 1-5: you know how `workflow.yaml` works, have run `rsf generate` and `rsf deploy`, and understand what RSF's built-in TerraformProvider produces
- Basic Terraform familiarity: you have run `terraform apply`, understand resources/modules/variables
- The RSF project cloned locally

Verify your tools are ready:

```bash
rsf --version
```

```bash
aws sts get-caller-identity
```

You should see your AWS account ID and ARN. If this fails, configure the AWS CLI with `aws configure`.

```bash
terraform --version
```

You should see `Terraform v1.5.7` or newer. The registry modules used in this tutorial require Terraform >= 1.5.7.

```bash
jq --version
```

`jq` is required by `deploy.sh` to parse RSF's metadata file. Install with `apt install jq` or `brew install jq`.

```bash
python3 --version
```

Python 3.13 is required for the Lambda runtime used in this tutorial.

> **Cost warning:** This tutorial deploys real AWS infrastructure. The following resources will be created in your account: a Lambda Durable Function, an IAM role with managed and inline policies, a DynamoDB table, an SQS dead-letter queue, an SNS topic, and three CloudWatch alarms. These resources incur costs while they exist. Step 10 shows you how to tear everything down cleanly.

---

## Step 1: Clone and Navigate

Navigate to the `registry-modules-demo` example directory:

```bash
cd examples/registry-modules-demo
```

The directory contains everything needed for this tutorial:

```
registry-modules-demo/
  workflow.yaml          # Image-processing pipeline definition
  rsf.toml               # Custom provider config (you will edit this)
  deploy.sh              # Invoked by RSF: zip source + terraform apply/destroy
  handlers/              # One handler file per Task state
    __init__.py
    validate_image.py
    resize_image.py
    analyze_content.py
    catalogue_image.py
  terraform/             # Terraform configuration using registry modules
    versions.tf          # Pinned provider and module versions
    main.tf              # Lambda module + aws_lambda_alias "live"
    dynamodb.tf          # DynamoDB table module (for_each pattern)
    sqs.tf               # SQS dead-letter queue (conditional count)
    alarms.tf            # CloudWatch alarms (locals alarm_by_type pattern)
    sns.tf               # SNS topic for alarm notifications
    iam_durable.tf       # IAM policy rationale documentation
    variables.tf         # All Terraform input variables
    outputs.tf           # alias_arn, function_name, role_arn, table ARNs
    backend.tf           # Local backend (state gitignored)
  build/                 # Created at deploy time (gitignored)
    function.zip
  src/generated/         # Created by rsf deploy (gitignored)
  tests/
    test_handlers.py     # 16 unit tests across all 4 handlers
```

---

## Step 2: Configure the Custom Provider

Open `rsf.toml`. It currently contains a placeholder path:

```toml
# RSF Custom Provider Configuration
# ---
# This example uses a custom provider (deploy.sh) to deploy via
# Terraform registry modules instead of RSF's built-in Terraform provider.
#
# IMPORTANT: Replace the program path below with your absolute path.
# Find it with:
#   echo "$(cd examples/registry-modules-demo && pwd)/deploy.sh"

[infrastructure]
provider = "custom"

[infrastructure.custom]
program         = "/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh"
args            = ["deploy"]
teardown_args   = ["destroy"]
metadata_transport = "file"
```

Find the absolute path to `deploy.sh`:

```bash
echo "$(cd examples/registry-modules-demo && pwd)/deploy.sh"
```

Expected output:

```
/home/your-user/git/rsf-python/examples/registry-modules-demo/deploy.sh
```

Replace the `program` field with your actual path:

```toml
[infrastructure]
provider = "custom"

[infrastructure.custom]
program         = "/home/your-user/git/rsf-python/examples/registry-modules-demo/deploy.sh"
args            = ["deploy"]
teardown_args   = ["destroy"]
metadata_transport = "file"
```

Each field explained:

- **`provider = "custom"`** — tells RSF to skip its built-in TerraformProvider and use the custom provider instead
- **`program`** — absolute path to the script RSF will execute. Must be absolute — RSF invokes this from an internal working directory that is not the project root
- **`args = ["deploy"]`** — passed to `deploy.sh` when running `rsf deploy`
- **`teardown_args = ["destroy"]`** — passed to `deploy.sh` when running `rsf deploy --teardown`
- **`metadata_transport = "file"`** — RSF writes `WorkflowMetadata` to a temp file and sets `RSF_METADATA_FILE` to its path before invoking the script. The script reads this file with `jq`

---

## Step 3: Make deploy.sh Executable

```bash
chmod +x examples/registry-modules-demo/deploy.sh
```

This is required because RSF invokes `deploy.sh` directly as an executable. Without `+x`, you will see a "permission denied" error when running `rsf deploy`.

---

## Step 4: Review the Workflow

Open `workflow.yaml`. It defines the image-processing pipeline:

```yaml
rsf_version: "1.0"
Comment: "image-processing"
StartAt: ValidateImage

dynamodb_tables:
  - table_name: image-catalogue
    partition_key:
      name: image_id
      type: S
    billing_mode: PAY_PER_REQUEST

dead_letter_queue:
  enabled: true
  max_receive_count: 3
  queue_name: image-processing-dlq

alarms:
  - type: error_rate
    threshold: 1
    period: 300
    evaluation_periods: 1
  - type: duration
    threshold: 10000
    period: 300
    evaluation_periods: 1
  - type: throttle
    threshold: 1
    period: 300
    evaluation_periods: 1

States:
  ValidateImage:
    Type: Task
    # ... Retry and Catch blocks ...
    Next: ResizeImage
  ResizeImage:
    Type: Task
    Next: AnalyzeContent
  AnalyzeContent:
    Type: Task
    Next: CatalogueImage
  CatalogueImage:
    Type: Task
    Next: ProcessingComplete
  ProcessingComplete:
    Type: Succeed
  ProcessingFailed:
    Type: Fail
```

Key points:

- **`Comment: "image-processing"`** — RSF uses this as `workflow_name` in `WorkflowMetadata`. It becomes the Lambda function name.
- **`dynamodb_tables`** — declares the `image-catalogue` table. RSF extracts this into `WorkflowMetadata.dynamodb_tables` and `deploy.sh` passes it to Terraform as a variable.
- **`dead_letter_queue`** — enables an SQS DLQ with 3-receive-count. Maps to `dlq_enabled`, `dlq_max_receive_count`, and `dlq_queue_name` in the metadata.
- **`alarms`** — three alarm configs (error rate, duration, throttle). `deploy.sh` strips the `sns_topic_arn` field before writing `terraform.tfvars.json` — SNS wiring is handled inside Terraform.
- **4 Task states** — each maps to a handler in `handlers/`. `ValidateImage` has a Retry/Catch block for `InvalidImageError`.

---

## Step 5: Review the Terraform

The `terraform/` directory uses 5 registry modules. Here is a walkthrough of the key files.

### terraform/versions.tf — Pinned versions

```hcl
terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.25.0"  # durable_config block added in v6.25.0
    }
  }
}
```

All module versions are pinned to exact strings (e.g., `version = "8.7.0"`) — not range constraints. See Step 9, Pitfall 4 for why.

### terraform/main.tf — Lambda + alias

The Lambda module creates the function, IAM role, and all policies in one call:

```hcl
module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.7.0"

  function_name = var.workflow_name
  handler       = "orchestrator.lambda_handler"
  runtime       = "python3.13"

  # Pre-built zip — deploy.sh creates build/function.zip before calling terraform
  create_package         = false
  local_existing_package = "${path.module}/../build/function.zip"

  # Lambda Durable Functions configuration
  durable_config_execution_timeout = coalesce(var.execution_timeout, 86400)
  durable_config_retention_period  = 14

  logging_log_format = "JSON"

  # Hybrid IAM — managed policy + inline supplement
  create_role                   = true
  attach_cloudwatch_logs_policy = true
  attach_policies               = true
  number_of_policies            = 1
  policies = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy"]

  attach_policy_json = true
  policy_json        = jsonencode({ /* InvokeFunction + DynamoDB + SQS */ })

  dead_letter_target_arn = var.dlq_enabled ? module.sqs_dlq[0].queue_arn : null
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = module.lambda.lambda_function_name
  function_version = module.lambda.lambda_function_version
}
```

The `aws_lambda_alias` is mandatory — always invoke durable functions via alias ARN, never `$LATEST`. See Pitfall 5 and `terraform/iam_durable.tf` for the IAM policy rationale.

### terraform/dynamodb.tf — Per-table for_each

```hcl
module "dynamodb_table" {
  source   = "terraform-aws-modules/dynamodb-table/aws"
  version  = "5.5.0"
  for_each = { for t in var.dynamodb_tables : t.table_name => t }

  name         = each.value.table_name
  hash_key     = each.value.partition_key.name
  billing_mode = each.value.billing_mode

  attributes = [{ name = each.value.partition_key.name, type = each.value.partition_key.type }]
}
```

`for_each` with a `table_name => t` map gives each instance a stable state key like `module.dynamodb_table["image-catalogue"]`.

### terraform/sqs.tf — Conditional DLQ

```hcl
module "sqs_dlq" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "5.2.1"
  count   = var.dlq_enabled ? 1 : 0

  name = var.dlq_queue_name != null ? var.dlq_queue_name : "${var.workflow_name}-dlq"
  message_retention_seconds = 1209600  # 14 days
}
```

`count = 0` when `dlq_enabled = false` — no SQS resources are created.

### terraform/alarms.tf — Type-keyed locals

```hcl
locals {
  alarm_by_type = { for a in var.alarms : a.type => a }
}

module "alarm_error_rate" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"
  count   = contains(keys(local.alarm_by_type), "error_rate") ? 1 : 0

  alarm_name         = "${var.workflow_name}-error-rate"
  metric_name        = "Errors"
  statistic          = "Sum"
  threshold          = local.alarm_by_type["error_rate"].threshold
  period             = local.alarm_by_type["error_rate"].period
  evaluation_periods = local.alarm_by_type["error_rate"].evaluation_periods
  alarm_actions      = [module.sns_alarms.topic_arn]
  dimensions         = { FunctionName = module.lambda.lambda_function_name }
}
```

The `alarm_by_type` locals map converts the alarms list to a map keyed by type, enabling O(1) lookups in `count` conditionals. The same pattern repeats for `duration` and `throttle`.

See the full `.tf` files in `examples/registry-modules-demo/terraform/` for complete configurations.

---

## Step 6: Deploy

From the project root, run:

```bash
rsf deploy examples/registry-modules-demo/workflow.yaml
```

RSF performs two steps before invoking `deploy.sh`:

1. Generates the orchestrator code into `examples/registry-modules-demo/src/generated/`
2. Writes `WorkflowMetadata` JSON to a temp file and sets `RSF_METADATA_FILE` to its path

Then it invokes `deploy.sh deploy`. The script runs four steps:

1. **Package** — bundles `orchestrator.py`, `handlers/`, and the `rsf.registry` runtime into `build/function.zip`
2. **Generate tfvars** — reads `RSF_METADATA_FILE` via `jq` and writes `terraform/terraform.tfvars.json`
3. **Terraform** — runs `terraform init` then `terraform apply -auto-approve -var-file=terraform.tfvars.json`
4. **Print alias ARN** — prints the `live` alias ARN with a sample `aws lambda invoke` command

Expected output (simplified):

```
=== registry-modules-demo deploy.sh ===
Command          : deploy
Workflow name    : image-processing

Packaged: /home/your-user/git/rsf-python/examples/registry-modules-demo/build/function.zip

Generated: /home/your-user/git/rsf-python/examples/registry-modules-demo/terraform/terraform.tfvars.json

Initializing the backend...
Initializing modules...
...
Terraform has been successfully initialized!

module.lambda.aws_iam_role.this[0]: Creating...
module.dynamodb_table["image-catalogue"].aws_dynamodb_table.this[0]: Creating...
module.sqs_dlq[0].aws_sqs_queue.this[0]: Creating...
...
Apply complete! Resources: 22 added, 0 changed, 0 destroyed.

=== Deploy complete ===
Alias ARN: arn:aws:lambda:us-east-2:123456789012:function:image-processing:live

Sample invocation:
  aws lambda invoke \
    --function-name 'arn:aws:lambda:us-east-2:123456789012:function:image-processing:live' \
    --payload '{"image_url": "s3://my-bucket/photo.jpg"}' \
    --cli-binary-format raw-in-base64-out \
    response.json && cat response.json
```

> The account ID (`123456789012`) and exact ARN values will differ in your output. The resource count may vary slightly.

---

## Step 7: Verify the Deployment

Check Terraform outputs from inside the Terraform directory:

```bash
terraform -chdir=examples/registry-modules-demo/terraform output
```

Expected output:

```
alias_arn           = "arn:aws:lambda:us-east-2:123456789012:function:image-processing:live"
dynamodb_table_arns = {
  "image-catalogue" = "arn:aws:dynamodb:us-east-2:123456789012:table/image-catalogue"
}
function_name       = "image-processing"
role_arn            = "arn:aws:iam::123456789012:role/image-processing"
sns_alarm_topic_arn = "arn:aws:sns:us-east-2:123456789012:image-processing-alarms"
sqs_dlq_url         = "https://sqs.us-east-2.amazonaws.com/123456789012/image-processing-dlq"
```

Invoke the Lambda using the alias ARN (copy the ARN from your deploy output):

```bash
aws lambda invoke \
  --function-name 'arn:aws:lambda:us-east-2:123456789012:function:image-processing:live' \
  --payload '{"image_url": "s3://my-bucket/photo.jpg"}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-2 \
  response.json && cat response.json
```

Expected output:

```json
{
  "image_url": "s3://my-bucket/photo.jpg",
  "validation": {"valid": true, "format": "jpeg", "file_size_kb": 0},
  "resize": {"width": 1920, "height": 1080, "format": "jpeg"},
  "analysis": {"tags": ["jpeg", "photo"], "format": "jpeg"},
  "catalogue": {"image_id": "...", "status": "catalogued", "catalogued_at": "..."}
}
```

Verify the DynamoDB table exists:

```bash
aws dynamodb describe-table \
  --table-name image-catalogue \
  --region us-east-2 \
  --query 'Table.{Name:TableName,Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}'
```

Expected output:

```json
{
    "Name": "image-catalogue",
    "Status": "ACTIVE",
    "BillingMode": "PAY_PER_REQUEST"
}
```

Verify the SQS dead-letter queue:

```bash
aws sqs get-queue-url \
  --queue-name image-processing-dlq \
  --region us-east-2
```

Expected output:

```json
{
    "QueueUrl": "https://sqs.us-east-2.amazonaws.com/123456789012/image-processing-dlq"
}
```

This confirms the deployment is complete: Lambda Durable Function, DynamoDB table, SQS DLQ, SNS topic, and CloudWatch alarms are all live.

---
