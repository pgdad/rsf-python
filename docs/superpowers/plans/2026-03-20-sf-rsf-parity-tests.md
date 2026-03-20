# Step Functions vs RSF Parity Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 parity tests that deploy identical workflows as both AWS Step Functions state machines and RSF Lambda Durable Functions, execute both with the same input, and compare final output, side effects, and execution trace.

**Architecture:** Each test has a Terraform module deploying both SF and RSF versions, shared handler code (pure logic reused by both), and a pytest harness that seeds data, runs both versions sequentially, resets state between runs, and compares results across 3 dimensions. A shared Terraform module provides S3, SQS, and IAM resources used by all tests.

**Tech Stack:** Terraform, boto3, pytest, RSF CLI, AWS (S3, SQS, Step Functions, Lambda Durable Functions, CloudWatch Logs, IAM)

**Spec:** `docs/superpowers/specs/2026-03-20-sf-rsf-parity-tests-design.md`

**Reference:** Existing integration test harness at `tests/test_examples/conftest.py` — reuse `terraform_deploy`, `terraform_teardown`, `poll_execution`, `query_logs`, `make_execution_id`, `iam_propagation_wait`.

---

## File Structure

### New Files

```
tests/parity/
├── conftest.py                               # Shared fixtures + parity comparison helpers
├── handlers/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── s3_utils.py                       # read_json_from_s3(), write_json_to_s3()
│   │   └── sqs_utils.py                      # poll_sqs(), delete_messages()
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── transform.py                      # transform_record() — pure logic
│   │   ├── rsf_handlers.py                   # @state decorators
│   │   └── sf_handler.py                     # Lambda entry point for SF
│   ├── sqs_collector/
│   │   ├── __init__.py
│   │   ├── rsf_handlers.py                   # @state: PollSQS, WriteToS3, DeleteMessages
│   │   └── sf_handler.py                     # SF Lambda for DeleteMessages
│   └── choice_routing/
│       ├── __init__.py
│       ├── process_csv.py                    # Pure logic: CSV → records
│       ├── process_json.py                   # Pure logic: JSON normalize
│       ├── rsf_handlers.py                   # @state handlers
│       └── sf_handler.py                     # SF Lambda entry points
├── shared/
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── test-01-etl/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── sfn_definition.json
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── workflow.yaml
│   ├── test_data/
│   │   └── input.json
│   └── test_etl_parity.py
├── test-02-sqs-collector/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── sfn_definition.json
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── workflow.yaml
│   ├── test_data/
│   │   └── messages.json
│   └── test_sqs_collector_parity.py
└── test-03-choice-routing/
    ├── terraform/
    │   ├── main.tf
    │   ├── sfn_definition.json
    │   ├── variables.tf
    │   └── outputs.tf
    ├── workflow.yaml
    ├── test_data/
    │   ├── config_csv.json
    │   ├── config_json.json
    │   ├── sample.csv
    │   └── sample.json
    └── test_choice_routing_parity.py
```

---

## Task 1: Shared Handler Utilities

**Files:**
- Create: `tests/parity/handlers/__init__.py`
- Create: `tests/parity/handlers/common/__init__.py`
- Create: `tests/parity/handlers/common/s3_utils.py`
- Create: `tests/parity/handlers/common/sqs_utils.py`

These utility functions are used by both RSF @state handlers and SF Lambda handlers. They wrap boto3 calls with the S3 bucket and SQS queue URL passed as parameters (not hardcoded — injected via environment variables at deploy time).

- [ ] **Step 1: Create s3_utils.py**

```python
"""S3 read/write utilities shared by RSF handlers and SF Lambda handlers."""

from __future__ import annotations

import json
import os

import boto3

_s3 = boto3.client("s3")


def get_bucket() -> str:
    """Return the S3 bucket name from environment."""
    return os.environ["PARITY_S3_BUCKET"]


def read_json_from_s3(key: str, bucket: str | None = None) -> dict | list:
    """Read and parse a JSON object from S3."""
    bucket = bucket or get_bucket()
    response = _s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def write_json_to_s3(key: str, data: dict | list, bucket: str | None = None) -> None:
    """Write a JSON-serializable object to S3."""
    bucket = bucket or get_bucket()
    _s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, default=str).encode("utf-8"),
        ContentType="application/json",
    )
```

- [ ] **Step 2: Create sqs_utils.py**

```python
"""SQS poll/delete utilities shared by RSF handlers and SF Lambda handlers."""

from __future__ import annotations

import json
import os

import boto3

_sqs = boto3.client("sqs")


def get_queue_url() -> str:
    """Return the SQS queue URL from environment."""
    return os.environ["PARITY_SQS_QUEUE_URL"]


def poll_sqs(queue_url: str | None = None, max_messages: int = 1) -> list[dict]:
    """Receive messages from SQS. Returns list of message dicts with Body and ReceiptHandle."""
    queue_url = queue_url or get_queue_url()
    response = _sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=5,
    )
    messages = response.get("Messages", [])
    return [
        {
            "body": json.loads(m["Body"]),
            "receipt_handle": m["ReceiptHandle"],
            "message_id": m["MessageId"],
        }
        for m in messages
    ]


def delete_messages(receipt_handles: list[str], queue_url: str | None = None) -> None:
    """Batch delete messages from SQS by receipt handle."""
    queue_url = queue_url or get_queue_url()
    if not receipt_handles:
        return
    entries = [
        {"Id": str(i), "ReceiptHandle": rh}
        for i, rh in enumerate(receipt_handles)
    ]
    _sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
```

- [ ] **Step 3: Create __init__.py files**

Create empty `tests/parity/handlers/__init__.py` and `tests/parity/handlers/common/__init__.py`.

- [ ] **Step 4: Commit**

```bash
git add tests/parity/handlers/
git commit -m "feat(parity): add shared S3 and SQS handler utilities"
```

---

## Task 2: ETL Handler Code

**Files:**
- Create: `tests/parity/handlers/etl/__init__.py`
- Create: `tests/parity/handlers/etl/transform.py`
- Create: `tests/parity/handlers/etl/rsf_handlers.py`
- Create: `tests/parity/handlers/etl/sf_handler.py`

- [ ] **Step 1: Create transform.py (pure logic)**

```python
"""Pure transformation logic — no AWS calls, no decorators.

Used by both RSF handlers and SF Lambda handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone


def transform_record(record: dict) -> dict:
    """Uppercase the 'name' field and add a 'processed_at' timestamp."""
    return {
        **record,
        "name": record.get("name", "").upper(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 2: Create rsf_handlers.py**

```python
"""RSF @state handlers for the ETL pipeline.

These handlers use boto3 for S3 operations (since RSF doesn't have
SDK integrations like Step Functions does).
"""

from __future__ import annotations

import json

from rsf.registry import state

from handlers.common.s3_utils import get_bucket, read_json_from_s3, write_json_to_s3
from handlers.etl.transform import transform_record


@state("ReadFromS3")
def read_from_s3(event: dict) -> dict:
    """Read input data from S3."""
    key = event["source_key"]
    data = read_json_from_s3(key)
    return {**event, "records": data}


@state("TransformOne")
def transform_one_handler(event: dict) -> dict:
    """Transform a single record (called per item in Map state)."""
    return transform_record(event)


@state("WriteETLResult")
def write_etl_result(event: dict) -> dict:
    """Write transformed records to S3."""
    output_key = event["output_key"]
    records = event["records"]
    write_json_to_s3(output_key, records)
    return {**event, "written": True, "output_key": output_key}
```

- [ ] **Step 3: Create sf_handler.py**

```python
"""SF Lambda handler for the ETL pipeline.

Only used for the Map state's TransformRecords — S3 read/write
use Step Functions AWS SDK integrations (arn:aws:states:::aws-sdk:s3:*).
"""

from __future__ import annotations

from handlers.etl.transform import transform_record


def handler(event: dict, context) -> dict:
    """Lambda entry point for SF Map task — transforms one record."""
    return transform_record(event)
```

- [ ] **Step 4: Create __init__.py**

Empty `tests/parity/handlers/etl/__init__.py`.

- [ ] **Step 5: Commit**

```bash
git add tests/parity/handlers/etl/
git commit -m "feat(parity): add ETL handler code (transform, RSF handlers, SF handler)"
```

---

## Task 3: SQS Collector Handler Code

**Files:**
- Create: `tests/parity/handlers/sqs_collector/__init__.py`
- Create: `tests/parity/handlers/sqs_collector/rsf_handlers.py`
- Create: `tests/parity/handlers/sqs_collector/sf_handler.py`

- [ ] **Step 1: Create rsf_handlers.py**

```python
"""RSF @state handlers for the SQS message collector.

PollSQS, WriteToS3, and DeleteMessages all use boto3 directly.
"""

from __future__ import annotations

from rsf.registry import state

from handlers.common.s3_utils import write_json_to_s3
from handlers.common.sqs_utils import poll_sqs, delete_messages


@state("PollSQS")
def poll_sqs_handler(event: dict) -> dict:
    """Poll SQS for one message."""
    messages = poll_sqs(max_messages=1)
    if messages:
        msg = messages[0]
        return {
            **event,
            "received": True,
            "message": msg["body"],
            "receipt_handle": msg["receipt_handle"],
        }
    return {**event, "received": False}


@state("WriteCollected")
def write_collected_handler(event: dict) -> dict:
    """Write collected messages to S3 as a JSON array."""
    output_key = event["output_key"]
    messages = event["messages"]
    write_json_to_s3(output_key, messages)
    return {**event, "written": True}


@state("DeleteMessages")
def delete_messages_handler(event: dict) -> dict:
    """Batch delete all collected messages from SQS."""
    receipt_handles = event.get("receipt_handles", [])
    delete_messages(receipt_handles)
    return {**event, "deleted": len(receipt_handles)}
```

- [ ] **Step 2: Create sf_handler.py**

```python
"""SF Lambda handlers for SQS collector.

Used for AppendMessage (array append) and DeleteMessages (batch delete).
PollSQS and WriteCollected use Step Functions AWS SDK integrations.
"""

from __future__ import annotations

import json
import os

import boto3

_sqs = boto3.client("sqs")


def append_handler(event: dict, context) -> dict:
    """Append a new message to the accumulated messages list.

    States.Array() creates nested arrays, so we use a Lambda for flat append.
    """
    messages = event.get("messages", [])
    receipt_handles = event.get("receipt_handles", [])
    new_message = event.get("new_message")
    new_receipt_handle = event.get("new_receipt_handle")

    # Parse the message body if it's a JSON string
    if isinstance(new_message, str):
        try:
            new_message = json.loads(new_message)
        except json.JSONDecodeError:
            pass

    messages.append(new_message)
    receipt_handles.append(new_receipt_handle)

    return {
        "messages": messages,
        "receipt_handles": receipt_handles,
        "count": len(messages),
        "queue_url": event.get("queue_url"),
        "output_key": event.get("output_key"),
        "s3_bucket": event.get("s3_bucket"),
    }


def delete_handler(event: dict, context) -> dict:
    """Batch delete messages from SQS."""
    queue_url = os.environ["PARITY_SQS_QUEUE_URL"]
    receipt_handles = event.get("receipt_handles", [])
    if not receipt_handles:
        return {"deleted": 0}
    entries = [
        {"Id": str(i), "ReceiptHandle": rh}
        for i, rh in enumerate(receipt_handles)
    ]
    _sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    return {"deleted": len(receipt_handles)}
```

- [ ] **Step 3: Create __init__.py**

Empty file.

- [ ] **Step 4: Commit**

```bash
git add tests/parity/handlers/sqs_collector/
git commit -m "feat(parity): add SQS collector handler code"
```

---

## Task 4: Choice Routing Handler Code

**Files:**
- Create: `tests/parity/handlers/choice_routing/__init__.py`
- Create: `tests/parity/handlers/choice_routing/process_csv.py`
- Create: `tests/parity/handlers/choice_routing/process_json.py`
- Create: `tests/parity/handlers/choice_routing/rsf_handlers.py`
- Create: `tests/parity/handlers/choice_routing/sf_handler.py`

- [ ] **Step 1: Create process_csv.py (pure logic)**

```python
"""Pure CSV processing logic — no AWS calls."""

from __future__ import annotations

import csv
import io


def process_csv(csv_text: str) -> list[dict]:
    """Parse CSV text into a list of record dicts."""
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]
```

- [ ] **Step 2: Create process_json.py (pure logic)**

```python
"""Pure JSON processing logic — no AWS calls."""

from __future__ import annotations


def process_json(records: list[dict]) -> list[dict]:
    """Validate and normalize JSON records.

    Normalizes field names to lowercase and adds a 'validated' flag.
    """
    normalized = []
    for record in records:
        normalized.append({
            k.lower(): v for k, v in record.items()
        } | {"validated": True})
    return normalized
```

- [ ] **Step 3: Create rsf_handlers.py**

```python
"""RSF @state handlers for choice-based format routing."""

from __future__ import annotations

import json

from rsf.registry import state

from handlers.common.s3_utils import read_json_from_s3, write_json_to_s3
from handlers.choice_routing.process_csv import process_csv
from handlers.choice_routing.process_json import process_json


@state("ReadConfig")
def read_config(event: dict) -> dict:
    """Read the config/job file from S3."""
    config = read_json_from_s3(event["config_key"])
    return {**event, **config}


@state("ProcessCSV")
def process_csv_handler(event: dict) -> dict:
    """Read CSV from S3 and process it."""
    csv_data = read_json_from_s3(event["source_key"])
    # source_key points to raw text stored as JSON string
    records = process_csv(csv_data if isinstance(csv_data, str) else json.dumps(csv_data))
    return {**event, "records": records, "record_count": len(records)}


@state("ProcessJSON")
def process_json_handler(event: dict) -> dict:
    """Read JSON from S3 and process it."""
    raw_records = read_json_from_s3(event["source_key"])
    records = process_json(raw_records)
    return {**event, "records": records, "record_count": len(records)}


@state("WriteResult")
def write_result(event: dict) -> dict:
    """Write processed records to the format-specific output prefix."""
    fmt = event["format"]
    output_key = f"{event['output_prefix']}/{fmt}/result.json"
    write_json_to_s3(output_key, event["records"])
    return {**event, "output_key": output_key, "written": True}
```

- [ ] **Step 4: Create sf_handler.py**

```python
"""SF Lambda handlers for choice-based format routing.

Used for ProcessCSV and ProcessJSON tasks. ReadConfig and WriteResult
use Step Functions AWS SDK integrations.
"""

from __future__ import annotations

import json

from handlers.choice_routing.process_csv import process_csv
from handlers.choice_routing.process_json import process_json


def csv_handler(event: dict, context) -> dict:
    """Lambda entry point for SF ProcessCSV task."""
    csv_text = event.get("csv_text", "")
    records = process_csv(csv_text)
    return {"records": records, "record_count": len(records)}


def json_handler(event: dict, context) -> dict:
    """Lambda entry point for SF ProcessJSON task."""
    raw_records = event.get("records", [])
    records = process_json(raw_records)
    return {"records": records, "record_count": len(records)}
```

- [ ] **Step 5: Create __init__.py and commit**

```bash
git add tests/parity/handlers/choice_routing/
git commit -m "feat(parity): add choice routing handler code (CSV, JSON processors)"
```

---

## Task 5: Shared Terraform Module

**Files:**
- Create: `tests/parity/shared/terraform/main.tf`
- Create: `tests/parity/shared/terraform/variables.tf`
- Create: `tests/parity/shared/terraform/outputs.tf`

- [ ] **Step 1: Create variables.tf**

```hcl
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
```

- [ ] **Step 2: Create main.tf**

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  bucket_name = "${var.name_prefix}-${random_id.suffix.hex}"
  queue_name  = "${var.name_prefix}-queue-${random_id.suffix.hex}"
  dlq_name    = "${var.name_prefix}-dlq-${random_id.suffix.hex}"
}

# --- S3 Bucket ---

resource "aws_s3_bucket" "parity" {
  bucket        = local.bucket_name
  force_destroy = true

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

resource "aws_s3_bucket_versioning" "parity" {
  bucket = aws_s3_bucket.parity.id
  versioning_configuration {
    status = "Enabled"
  }
}

# --- SQS Queues ---

resource "aws_sqs_queue" "dlq" {
  name                      = local.dlq_name
  message_retention_seconds = 300

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

resource "aws_sqs_queue" "parity" {
  name                       = local.queue_name
  visibility_timeout_seconds = 30
  message_retention_seconds  = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

# --- IAM Role for Lambda Handlers ---

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.name_prefix}-lambda-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }

  statement {
    sid = "S3Access"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.parity.arn}/*"]
  }

  statement {
    sid = "SQSAccess"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:DeleteMessageBatch",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.parity.arn]
  }

  statement {
    sid       = "LambdaSelfInvoke"
    actions   = ["lambda:InvokeFunction"]
    resources = ["*"]
  }

  statement {
    sid = "DurableExecution"
    actions = [
      "lambda:Checkpoint",
      "lambda:GetDurableExecution",
      "lambda:GetDurableExecutionState",
      "lambda:ListDurableExecutionsByFunction",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.name_prefix}-lambda-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# --- IAM Role for Step Functions ---

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn_role" {
  name               = "${var.name_prefix}-sfn-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json

  tags = {
    ManagedBy = "rsf-parity-tests"
  }
}

data "aws_iam_policy_document" "sfn_policy" {
  statement {
    sid = "InvokeLambda"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = ["*"]
  }

  statement {
    sid = "S3Access"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.parity.arn}/*"]
  }

  statement {
    sid = "SQSAccess"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:DeleteMessageBatch",
      "sqs:SendMessage",
    ]
    resources = [aws_sqs_queue.parity.arn]
  }

  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn_policy" {
  name   = "${var.name_prefix}-sfn-policy"
  role   = aws_iam_role.sfn_role.id
  policy = data.aws_iam_policy_document.sfn_policy.json
}
```

- [ ] **Step 3: Create outputs.tf**

```hcl
output "s3_bucket_name" {
  description = "S3 bucket for parity test data"
  value       = aws_s3_bucket.parity.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.parity.arn
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.parity.url
}

output "sqs_queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.parity.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda handlers"
  value       = aws_iam_role.lambda_role.arn
}

output "sfn_role_arn" {
  description = "IAM role ARN for Step Functions"
  value       = aws_iam_role.sfn_role.arn
}
```

- [ ] **Step 4: Verify Terraform validates**

Run: `cd tests/parity/shared/terraform && terraform init && terraform validate`
Expected: "Success! The configuration is valid."

- [ ] **Step 5: Commit**

```bash
git add tests/parity/shared/
git commit -m "feat(parity): add shared Terraform module (S3, SQS, IAM)"
```

---

## Task 6: Test Data Files

**Files:**
- Create: `tests/parity/test-01-etl/test_data/input.json`
- Create: `tests/parity/test-02-sqs-collector/test_data/messages.json`
- Create: `tests/parity/test-03-choice-routing/test_data/config_csv.json`
- Create: `tests/parity/test-03-choice-routing/test_data/config_json.json`
- Create: `tests/parity/test-03-choice-routing/test_data/sample.csv`
- Create: `tests/parity/test-03-choice-routing/test_data/sample.json`

- [ ] **Step 1: Create ETL input data**

Create `tests/parity/test-01-etl/test_data/input.json`:

```json
[
  {"name": "alice", "age": 30, "department": "engineering"},
  {"name": "bob", "age": 25, "department": "marketing"},
  {"name": "carol", "age": 35, "department": "engineering"},
  {"name": "dave", "age": 28, "department": "sales"},
  {"name": "eve", "age": 32, "department": "marketing"}
]
```

- [ ] **Step 2: Create SQS messages data**

Create `tests/parity/test-02-sqs-collector/test_data/messages.json`:

```json
[
  {"event_type": "page_view", "page": "/home", "user_id": "u001"},
  {"event_type": "click", "element": "buy_button", "user_id": "u002"},
  {"event_type": "page_view", "page": "/products", "user_id": "u003"},
  {"event_type": "signup", "email": "test@example.com", "user_id": "u004"},
  {"event_type": "click", "element": "search_bar", "user_id": "u005"},
  {"event_type": "page_view", "page": "/checkout", "user_id": "u001"},
  {"event_type": "purchase", "amount": 59.99, "user_id": "u002"},
  {"event_type": "page_view", "page": "/about", "user_id": "u006"},
  {"event_type": "click", "element": "nav_menu", "user_id": "u003"},
  {"event_type": "logout", "user_id": "u001"}
]
```

- [ ] **Step 3: Create choice routing test data**

Create `tests/parity/test-03-choice-routing/test_data/config_csv.json`:
```json
{"format": "csv", "source_key": "input/choice-routing/sample.csv"}
```

Create `tests/parity/test-03-choice-routing/test_data/config_json.json`:
```json
{"format": "json", "source_key": "input/choice-routing/sample.json"}
```

Create `tests/parity/test-03-choice-routing/test_data/sample.csv`:
```csv
name,age,department
alice,30,engineering
bob,25,marketing
carol,35,engineering
```

Create `tests/parity/test-03-choice-routing/test_data/sample.json`:
```json
[
  {"Name": "alice", "Age": 30, "Department": "engineering"},
  {"Name": "bob", "Age": 25, "Department": "marketing"},
  {"Name": "carol", "Age": 35, "Department": "engineering"}
]
```

- [ ] **Step 4: Commit**

```bash
git add tests/parity/test-01-etl/test_data/ tests/parity/test-02-sqs-collector/test_data/ tests/parity/test-03-choice-routing/test_data/
git commit -m "feat(parity): add test data files for all 3 parity tests"
```

---

## Task 7: RSF Workflow Definitions

**Files:**
- Create: `tests/parity/test-01-etl/workflow.yaml`
- Create: `tests/parity/test-02-sqs-collector/workflow.yaml`
- Create: `tests/parity/test-03-choice-routing/workflow.yaml`

- [ ] **Step 1: Create ETL workflow.yaml**

```yaml
rsf_version: "1.0"
Comment: "Parity test: S3 ETL pipeline"
StartAt: ReadFromS3

States:
  ReadFromS3:
    Type: Task
    Next: TransformRecords

  TransformRecords:
    Type: Map
    ItemsPath: "$.records"
    ItemProcessor:
      StartAt: TransformOne
      States:
        TransformOne:
          Type: Task
          End: true
    ResultPath: "$.records"
    Next: WriteETLResult

  WriteETLResult:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
```

Note: The Map state's inner task is named "TransformOne" in the ItemProcessor. The RSF handler is registered as `@state("TransformOne")` to match.

- [ ] **Step 2: Create SQS collector workflow.yaml**

```yaml
rsf_version: "1.0"
Comment: "Parity test: SQS message collector"
StartAt: Initialize

States:
  Initialize:
    Type: Pass
    Result:
      messages: []
      receipt_handles: []
      count: 0
    Next: PollSQS

  PollSQS:
    Type: Task
    ResultPath: "$.poll_result"
    Next: CheckMessages

  CheckMessages:
    Type: Choice
    Choices:
      - Variable: "$.poll_result.received"
        BooleanEquals: true
        Next: AppendMessage
    Default: WaitBeforePoll

  AppendMessage:
    Type: Pass
    Next: CheckCount

  CheckCount:
    Type: Choice
    Choices:
      - Variable: "$.count"
        NumericGreaterThanEquals: 10
        Next: WriteCollected
    Default: WaitBeforePoll

  WaitBeforePoll:
    Type: Wait
    Seconds: 10
    Next: PollSQS

  WriteCollected:
    Type: Task
    Next: DeleteMessages

  DeleteMessages:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
```

Note: The AppendMessage Pass state will need Parameters/ResultPath to actually append the message. The exact I/O pipeline for accumulating messages in the RSF version needs careful design. The RSF handler for PollSQS returns the message; AppendMessage (Pass) must merge it into the messages array. This is a limitation — RSF Pass states support Result and ResultPath but not array append. The handler-based approach is more practical: have PollSQS return the updated messages array directly.

- [ ] **Step 3: Create choice routing workflow.yaml**

```yaml
rsf_version: "1.0"
Comment: "Parity test: choice-based format routing"
StartAt: ReadConfig

States:
  ReadConfig:
    Type: Task
    Next: RouteByFormat

  RouteByFormat:
    Type: Choice
    Choices:
      - Variable: "$.format"
        StringEquals: "csv"
        Next: ProcessCSV
      - Variable: "$.format"
        StringEquals: "json"
        Next: ProcessJSON
    Default: HandleUnknownFormat

  ProcessCSV:
    Type: Task
    Next: WriteResult

  ProcessJSON:
    Type: Task
    Next: WriteResult

  WriteResult:
    Type: Task
    Next: Done

  HandleUnknownFormat:
    Type: Fail
    Error: "UnsupportedFormat"
    Cause: "The format field must be 'csv' or 'json'"

  Done:
    Type: Succeed
```

- [ ] **Step 4: Commit**

```bash
git add tests/parity/test-01-etl/workflow.yaml tests/parity/test-02-sqs-collector/workflow.yaml tests/parity/test-03-choice-routing/workflow.yaml
git commit -m "feat(parity): add RSF workflow definitions for all 3 parity tests"
```

---

## Task 8: Step Functions ASL Definitions

**Files:**
- Create: `tests/parity/test-01-etl/terraform/sfn_definition.json`
- Create: `tests/parity/test-02-sqs-collector/terraform/sfn_definition.json`
- Create: `tests/parity/test-03-choice-routing/terraform/sfn_definition.json`

These are the equivalent ASL JSON definitions using AWS SDK integrations for S3/SQS where possible.

- [ ] **Step 1: Create ETL ASL definition**

Create `tests/parity/test-01-etl/terraform/sfn_definition.json`. This uses AWS SDK integrations for S3 and a Lambda function for the Map transform. Use Terraform template variables for the Lambda ARN and bucket name:

```json
{
  "Comment": "Parity test: S3 ETL pipeline (Step Functions version)",
  "StartAt": "ReadFromS3",
  "States": {
    "ReadFromS3": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
      "Parameters": {
        "Bucket": "${s3_bucket}",
        "Key.$": "$.source_key"
      },
      "ResultSelector": {
        "records.$": "States.StringToJson($.Body)"
      },
      "ResultPath": "$.s3_result",
      "Next": "PrepareRecords"
    },
    "PrepareRecords": {
      "Type": "Pass",
      "InputPath": "$.s3_result.records",
      "ResultPath": "$.records",
      "Next": "TransformRecords"
    },
    "TransformRecords": {
      "Type": "Map",
      "ItemsPath": "$.records",
      "ItemProcessor": {
        "StartAt": "TransformOne",
        "States": {
          "TransformOne": {
            "Type": "Task",
            "Resource": "${transform_lambda_arn}",
            "End": true
          }
        }
      },
      "ResultPath": "$.records",
      "Next": "WriteETLResult"
    },
    "WriteETLResult": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:putObject",
      "Parameters": {
        "Bucket": "${s3_bucket}",
        "Key.$": "$.output_key",
        "Body.$": "States.JsonToString($.records)",
        "ContentType": "application/json"
      },
      "ResultPath": "$.write_result",
      "Next": "Done"
    },
    "Done": {
      "Type": "Succeed"
    }
  }
}
```

Note: The ASL JSON uses Terraform `templatefile()` variables (`${s3_bucket}`, `${transform_lambda_arn}`) that will be substituted at deploy time.

- [ ] **Step 2: Create SQS collector ASL definition**

Create `tests/parity/test-02-sqs-collector/terraform/sfn_definition.json`:

```json
{
  "Comment": "Parity test: SQS message collector (Step Functions version)",
  "StartAt": "Initialize",
  "States": {
    "Initialize": {
      "Type": "Pass",
      "Result": {
        "messages": [],
        "receipt_handles": [],
        "count": 0,
        "queue_url": "${sqs_queue_url}",
        "output_key": "${output_key_prefix}/result.json",
        "s3_bucket": "${s3_bucket}"
      },
      "Next": "PollSQS"
    },
    "PollSQS": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:sqs:receiveMessage",
      "Parameters": {
        "QueueUrl.$": "$.queue_url",
        "MaxNumberOfMessages": 1,
        "WaitTimeSeconds": 5
      },
      "ResultPath": "$.poll_result",
      "Next": "CheckMessages"
    },
    "CheckMessages": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.poll_result.Messages[0]",
          "IsPresent": true,
          "Next": "AppendMessage"
        }
      ],
      "Default": "WaitBeforePoll"
    },
    "AppendMessage": {
      "Type": "Task",
      "Resource": "${append_lambda_arn}",
      "Parameters": {
        "messages.$": "$.messages",
        "receipt_handles.$": "$.receipt_handles",
        "count.$": "$.count",
        "new_message.$": "$.poll_result.Messages[0].Body",
        "new_receipt_handle.$": "$.poll_result.Messages[0].ReceiptHandle",
        "queue_url.$": "$.queue_url",
        "output_key.$": "$.output_key",
        "s3_bucket.$": "$.s3_bucket"
      },
      "Next": "CheckCount"
    },
    "CheckCount": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.count",
          "NumericGreaterThanEquals": 10,
          "Next": "WriteCollected"
        }
      ],
      "Default": "WaitBeforePoll"
    },
    "WaitBeforePoll": {
      "Type": "Wait",
      "Seconds": 10,
      "Next": "PollSQS"
    },
    "WriteCollected": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:putObject",
      "Parameters": {
        "Bucket.$": "$.s3_bucket",
        "Key.$": "$.output_key",
        "Body.$": "States.JsonToString($.messages)",
        "ContentType": "application/json"
      },
      "ResultPath": "$.write_result",
      "Next": "DeleteMessages"
    },
    "DeleteMessages": {
      "Type": "Task",
      "Resource": "${delete_lambda_arn}",
      "Parameters": {
        "receipt_handles.$": "$.receipt_handles"
      },
      "ResultPath": "$.delete_result",
      "Next": "Done"
    },
    "Done": {
      "Type": "Succeed"
    }
  }
}
```

Note: AppendMessage uses a Lambda function because Step Functions intrinsic functions (`States.Array()`) create nested arrays rather than appending to flat arrays. The Lambda handler receives the current state and the new message, appends it to the messages list, and returns the updated state. The `$.poll_result.Messages[0]` path accesses the SQS response format.

- [ ] **Step 3: Create choice routing ASL definition**

Create `tests/parity/test-03-choice-routing/terraform/sfn_definition.json`:

```json
{
  "Comment": "Parity test: choice-based format routing (Step Functions version)",
  "StartAt": "ReadConfig",
  "States": {
    "ReadConfig": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
      "Parameters": {
        "Bucket": "${s3_bucket}",
        "Key.$": "$.config_key"
      },
      "ResultSelector": {
        "config.$": "States.StringToJson($.Body)"
      },
      "ResultPath": "$.s3_result",
      "Next": "ExtractConfig"
    },
    "ExtractConfig": {
      "Type": "Pass",
      "Parameters": {
        "format.$": "$.s3_result.config.format",
        "source_key.$": "$.s3_result.config.source_key",
        "output_prefix.$": "$.output_prefix",
        "s3_bucket.$": "$.s3_bucket"
      },
      "Next": "RouteByFormat"
    },
    "RouteByFormat": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.format",
          "StringEquals": "csv",
          "Next": "ReadSourceCSV"
        },
        {
          "Variable": "$.format",
          "StringEquals": "json",
          "Next": "ReadSourceJSON"
        }
      ],
      "Default": "HandleUnknownFormat"
    },
    "ReadSourceCSV": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
      "Parameters": {
        "Bucket.$": "$.s3_bucket",
        "Key.$": "$.source_key"
      },
      "ResultSelector": {
        "csv_text.$": "$.Body"
      },
      "ResultPath": "$.source_data",
      "Next": "ProcessCSV"
    },
    "ProcessCSV": {
      "Type": "Task",
      "Resource": "${csv_lambda_arn}",
      "Parameters": {
        "csv_text.$": "$.source_data.csv_text"
      },
      "ResultPath": "$.processed",
      "Next": "WriteResult"
    },
    "ReadSourceJSON": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
      "Parameters": {
        "Bucket.$": "$.s3_bucket",
        "Key.$": "$.source_key"
      },
      "ResultSelector": {
        "records.$": "States.StringToJson($.Body)"
      },
      "ResultPath": "$.source_data",
      "Next": "ProcessJSON"
    },
    "ProcessJSON": {
      "Type": "Task",
      "Resource": "${json_lambda_arn}",
      "Parameters": {
        "records.$": "$.source_data.records"
      },
      "ResultPath": "$.processed",
      "Next": "WriteResult"
    },
    "WriteResult": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:s3:putObject",
      "Parameters": {
        "Bucket.$": "$.s3_bucket",
        "Key.$": "States.Format('{}/{}/result.json', $.output_prefix, $.format)",
        "Body.$": "States.JsonToString($.processed.records)",
        "ContentType": "application/json"
      },
      "ResultPath": "$.write_result",
      "Next": "Done"
    },
    "HandleUnknownFormat": {
      "Type": "Fail",
      "Error": "UnsupportedFormat",
      "Cause": "The format field must be 'csv' or 'json'"
    },
    "Done": {
      "Type": "Succeed"
    }
  }
}
```

Note: The SF version needs extra states (ReadSourceCSV, ReadSourceJSON) because S3 reads use SDK integrations, unlike RSF which reads S3 inside the handler. The SF version also splits the S3 read for each format branch, while the RSF ProcessCSV/ProcessJSON handlers do the S3 read internally.

- [ ] **Step 4: Commit**

```bash
git add tests/parity/test-01-etl/terraform/sfn_definition.json tests/parity/test-02-sqs-collector/terraform/sfn_definition.json tests/parity/test-03-choice-routing/terraform/sfn_definition.json
git commit -m "feat(parity): add Step Functions ASL definitions for all 3 parity tests"
```

---

## Task 9: Per-Test Terraform Modules

**Files:**
- Create: `tests/parity/test-01-etl/terraform/main.tf`
- Create: `tests/parity/test-01-etl/terraform/variables.tf`
- Create: `tests/parity/test-01-etl/terraform/outputs.tf`
- Create: `tests/parity/test-02-sqs-collector/terraform/main.tf`
- Create: `tests/parity/test-02-sqs-collector/terraform/variables.tf`
- Create: `tests/parity/test-02-sqs-collector/terraform/outputs.tf`
- Create: `tests/parity/test-03-choice-routing/terraform/main.tf`
- Create: `tests/parity/test-03-choice-routing/terraform/variables.tf`
- Create: `tests/parity/test-03-choice-routing/terraform/outputs.tf`

Each module deploys the SF state machine, SF handler Lambdas (where needed), and the RSF durable Lambda + alias. All reference the shared IAM roles and S3/SQS resources.

This is a large task — the implementer should create all 9 files following the pattern established by the existing `examples/order-processing/terraform/` module.

Key patterns to follow:
- `data "archive_file"` for zipping handler code
- `aws_lambda_function` with `handler`, `runtime = "python3.13"`, `role` from shared
- RSF Lambda gets `durable_config { execution_timeout = 600; retention_period = 1 }` and `logging_config { log_format = "JSON" }`
- `aws_lambda_alias "live"` for RSF Lambda pointing to `$LATEST`
- `aws_sfn_state_machine` using `templatefile("sfn_definition.json", { ... })` for definition
- Environment variables: `PARITY_S3_BUCKET`, `PARITY_SQS_QUEUE_URL` on all Lambdas
- `lifecycle { ignore_changes = [filename, source_code_hash] }` on Lambda functions

Each module's variables.tf takes: `aws_region`, `s3_bucket_name`, `sqs_queue_url`, `sqs_queue_arn`, `lambda_role_arn`, `sfn_role_arn`, `name_prefix`.

Each module's outputs.tf exports: `sfn_arn`, `rsf_function_name`, `rsf_alias_arn`, `rsf_log_group_name`.

- [ ] **Step 1: Create test-01-etl Terraform module**

The ETL module deploys:
- SF handler Lambda for TransformOne (Map item processor)
- SF state machine using sfn_definition.json
- RSF durable Lambda + alias

**`tests/parity/test-01-etl/terraform/variables.tf`:**

```hcl
variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "name_prefix" {
  type    = string
  default = "rsf-parity-etl"
}

variable "s3_bucket_name" {
  description = "Shared S3 bucket name"
  type        = string
}

variable "lambda_role_arn" {
  description = "Shared IAM role ARN for Lambda"
  type        = string
}

variable "sfn_role_arn" {
  description = "Shared IAM role ARN for Step Functions"
  type        = string
}
```

**`tests/parity/test-01-etl/terraform/main.tf`:**

```hcl
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

# --- SF Handler Lambda (TransformOne for Map state) ---

data "archive_file" "sf_handler_zip" {
  type        = "zip"
  source_dir  = local.handlers_dir
  output_path = "${path.module}/sf_handler.zip"
}

resource "aws_lambda_function" "sf_transform" {
  function_name    = "${var.name_prefix}-sf-transform"
  handler          = "etl.sf_handler.handler"
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

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# --- Step Functions State Machine ---

resource "aws_sfn_state_machine" "etl" {
  name     = "${var.name_prefix}-sf"
  role_arn = var.sfn_role_arn

  definition = templatefile("${path.module}/sfn_definition.json", {
    s3_bucket            = var.s3_bucket_name
    transform_lambda_arn = aws_lambda_function.sf_transform.arn
  })
}

# --- RSF Durable Lambda ---

data "archive_file" "rsf_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/rsf_etl.zip"
}

resource "aws_lambda_function" "rsf_etl" {
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

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_lambda_alias" "rsf_live" {
  name             = "live"
  function_name    = aws_lambda_function.rsf_etl.function_name
  function_version = "$LATEST"
}

resource "aws_cloudwatch_log_group" "rsf_logs" {
  name              = "/aws/lambda/${aws_lambda_function.rsf_etl.function_name}"
  retention_in_days = 1
}
```

**`tests/parity/test-01-etl/terraform/outputs.tf`:**

```hcl
output "sfn_arn" {
  value = aws_sfn_state_machine.etl.arn
}

output "rsf_function_name" {
  value = aws_lambda_function.rsf_etl.function_name
}

output "rsf_alias_arn" {
  value = aws_lambda_alias.rsf_live.arn
}

output "rsf_log_group_name" {
  value = aws_cloudwatch_log_group.rsf_logs.name
}
```

**Important packaging notes for all 3 modules:**
- SF handler Lambda zips `tests/parity/handlers/` as source_dir. Handler entry point is `{test_module}.sf_handler.handler` (e.g., `etl.sf_handler.handler`). The handlers import `from common.s3_utils import ...` etc. since `handlers/` is the ZIP root.
- RSF Lambda zips a `src/` directory under each test that contains the generated orchestrator + handlers. Before deploy, the implementer must: (1) `rsf generate` from the test's workflow.yaml, and (2) symlink or copy the handlers into `src/handlers/`. The RSF handler imports use `from handlers.common.s3_utils import ...` matching the `src/` root.
- SQS collector module needs two SF Lambdas (append + delete), so its sf_handler.py exports two entry points: `sqs_collector.sf_handler.append_handler` and `sqs_collector.sf_handler.delete_handler`.
- Choice routing module needs two SF Lambdas (CSV + JSON), entry points: `choice_routing.sf_handler.csv_handler` and `choice_routing.sf_handler.json_handler`.

- [ ] **Step 2: Create test-02-sqs-collector Terraform module**

The SQS collector module deploys:
- SF handler Lambda for DeleteMessages
- SF state machine using sfn_definition.json
- RSF durable Lambda + alias

- [ ] **Step 3: Create test-03-choice-routing Terraform module**

The choice routing module deploys:
- SF handler Lambda for ProcessCSV
- SF handler Lambda for ProcessJSON
- SF state machine using sfn_definition.json
- RSF durable Lambda + alias

- [ ] **Step 4: Verify all modules validate**

```bash
cd tests/parity/test-01-etl/terraform && terraform init && terraform validate
cd tests/parity/test-02-sqs-collector/terraform && terraform init && terraform validate
cd tests/parity/test-03-choice-routing/terraform && terraform init && terraform validate
```

- [ ] **Step 5: Commit**

```bash
git add tests/parity/test-01-etl/terraform/ tests/parity/test-02-sqs-collector/terraform/ tests/parity/test-03-choice-routing/terraform/
git commit -m "feat(parity): add per-test Terraform modules (SF + RSF for all 3 tests)"
```

---

## Task 10: Test Harness (conftest.py)

**Files:**
- Create: `tests/parity/conftest.py`

This builds on the existing `tests/test_examples/conftest.py` helpers. It adds:
- Session-scoped shared infrastructure fixture (deploy/teardown shared TF)
- Function-scoped per-test infrastructure fixture
- SF execution helpers (start_execution, describe_execution, get_execution_history)
- Parity comparison helpers (compare_outputs, compare_traces)
- Test data seeding helpers (upload to S3, send SQS messages)

- [ ] **Step 1: Create conftest.py**

```python
"""Shared parity test harness.

Extends tests/test_examples/conftest.py helpers with Step Functions
execution, trace comparison, and data seeding utilities.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import pytest

# Reuse existing integration test helpers
from tests.test_examples.conftest import (
    iam_propagation_wait,
    make_execution_id,
    poll_execution,
    query_logs,
    terraform_deploy,
    terraform_teardown,
)

logger = logging.getLogger(__name__)

PARITY_ROOT = Path(__file__).parent
PROJECT_ROOT = PARITY_ROOT.parent.parent

# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "parity: Step Functions vs RSF parity tests (require AWS credentials and terraform)",
    )


# ---------------------------------------------------------------------------
# AWS clients (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def aws_region():
    return "us-east-2"


@pytest.fixture(scope="session")
def s3_client(aws_region):
    return boto3.client("s3", region_name=aws_region)


@pytest.fixture(scope="session")
def sqs_client(aws_region):
    return boto3.client("sqs", region_name=aws_region)


@pytest.fixture(scope="session")
def sfn_client(aws_region):
    return boto3.client("stepfunctions", region_name=aws_region)


@pytest.fixture(scope="session")
def lambda_client(aws_region):
    return boto3.client("lambda", region_name=aws_region)


@pytest.fixture(scope="session")
def logs_client(aws_region):
    return boto3.client("logs", region_name=aws_region)


# ---------------------------------------------------------------------------
# Shared infrastructure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def shared_infra(logs_client):
    """Deploy shared Terraform (S3, SQS, IAM). Teardown at session end."""
    shared_dir = PARITY_ROOT / "shared"
    outputs = terraform_deploy(shared_dir)
    iam_propagation_wait()

    yield outputs

    terraform_teardown(shared_dir)


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------


@dataclass
class StateTransition:
    state_name: str
    status: str  # entered, succeeded, failed


# ---------------------------------------------------------------------------
# Step Functions execution helpers
# ---------------------------------------------------------------------------


def start_sf_execution(
    sfn_client: Any,
    state_machine_arn: str,
    input_data: dict,
    name: str | None = None,
) -> str:
    """Start a Step Functions execution. Returns execution ARN."""
    name = name or f"parity-{uuid.uuid4().hex[:8]}"
    response = sfn_client.start_execution(
        stateMachineArn=state_machine_arn,
        name=name,
        input=json.dumps(input_data),
    )
    return response["executionArn"]


def poll_sf_execution(
    sfn_client: Any,
    execution_arn: str,
    timeout: float = 300,
    poll_interval: float = 5.0,
) -> dict:
    """Poll Step Functions execution until terminal state."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = sfn_client.describe_execution(executionArn=execution_arn)
        status = response["status"]
        if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
            return response
        time.sleep(poll_interval)
    raise TimeoutError(f"SF execution {execution_arn} did not complete within {timeout}s")


def get_sf_trace(sfn_client: Any, execution_arn: str) -> list[StateTransition]:
    """Extract state transitions from Step Functions execution history."""
    transitions = []
    paginator = sfn_client.get_paginator("get_execution_history")
    for page in paginator.paginate(executionArn=execution_arn):
        for event in page["events"]:
            event_type = event["type"]
            # Map SF event types to state transitions
            if "StateEntered" in event_type:
                detail = event.get("stateEnteredEventDetails", {})
                transitions.append(StateTransition(
                    state_name=detail.get("name", ""),
                    status="entered",
                ))
            elif "StateExited" in event_type:
                detail = event.get("stateExitedEventDetails", {})
                transitions.append(StateTransition(
                    state_name=detail.get("name", ""),
                    status="succeeded",
                ))
    return transitions


# ---------------------------------------------------------------------------
# RSF trace extraction
# ---------------------------------------------------------------------------


def get_rsf_trace(
    logs_client: Any,
    log_group: str,
    start_time: datetime,
) -> list[StateTransition]:
    """Extract state transitions from RSF CloudWatch logs."""
    messages = query_logs(
        logs_client,
        log_group,
        "step_name",
        start_time,
        propagation_wait=15.0,
        max_retries=5,
    )
    transitions = []
    for msg in messages:
        try:
            data = json.loads(msg)
            transitions.append(StateTransition(
                state_name=data.get("step_name", ""),
                status="entered" if "starting" in msg.lower() else "succeeded",
            ))
        except json.JSONDecodeError:
            continue
    return transitions


# ---------------------------------------------------------------------------
# Parity comparison
# ---------------------------------------------------------------------------


def compare_state_sequences(
    sf_trace: list[StateTransition],
    rsf_trace: list[StateTransition],
    sf_extra_states: set[str] | None = None,
) -> bool:
    """Compare the sequence of states entered (ignoring timing).

    sf_extra_states: states present in SF but not RSF (e.g., extra S3 read
    states added because SF uses SDK integrations). These are excluded from
    the SF trace before comparison.
    """
    exclude = sf_extra_states or set()
    sf_states = [t.state_name for t in sf_trace if t.status == "entered" and t.state_name not in exclude]
    rsf_states = [t.state_name for t in rsf_trace if t.status == "entered"]
    return sf_states == rsf_states


def compare_s3_outputs(
    s3_client: Any,
    bucket: str,
    sf_key: str,
    rsf_key: str,
    ignore_fields: list[str] | None = None,
) -> bool:
    """Compare JSON objects written to S3 by SF and RSF.

    Optionally ignores fields that are expected to differ (e.g., timestamps).
    """
    sf_data = json.loads(
        s3_client.get_object(Bucket=bucket, Key=sf_key)["Body"].read()
    )
    rsf_data = json.loads(
        s3_client.get_object(Bucket=bucket, Key=rsf_key)["Body"].read()
    )

    if ignore_fields:
        sf_data = _strip_fields(sf_data, ignore_fields)
        rsf_data = _strip_fields(rsf_data, ignore_fields)

    return sf_data == rsf_data


def _strip_fields(data: Any, fields: list[str]) -> Any:
    """Recursively remove specified fields from nested dicts/lists."""
    if isinstance(data, dict):
        return {k: _strip_fields(v, fields) for k, v in data.items() if k not in fields}
    if isinstance(data, list):
        return [_strip_fields(item, fields) for item in data]
    return data


# ---------------------------------------------------------------------------
# Test data seeding
# ---------------------------------------------------------------------------


def upload_test_file(s3_client: Any, bucket: str, key: str, local_path: Path) -> None:
    """Upload a local file to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=local_path.read_bytes(),
        ContentType="application/json" if local_path.suffix == ".json" else "text/plain",
    )


def send_sqs_messages(
    sqs_client: Any,
    queue_url: str,
    messages: list[dict],
    stagger_seconds: float = 9.0,
) -> None:
    """Send messages to SQS with staggered timing (in a background thread)."""
    def _send():
        for i, msg in enumerate(messages):
            sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(msg),
            )
            logger.info("Sent SQS message %d/%d", i + 1, len(messages))
            if i < len(messages) - 1:
                time.sleep(stagger_seconds)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
    return thread


def purge_sqs_queue(sqs_client: Any, queue_url: str) -> None:
    """Drain all messages from an SQS queue.

    Uses receive + delete rather than PurgeQueue to avoid the 60-second
    cooldown between PurgeQueue calls (which would fail between SF and RSF runs).
    """
    while True:
        resp = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=2)
        msgs = resp.get("Messages", [])
        if not msgs:
            break
        entries = [{"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]} for i, m in enumerate(msgs)]
        sqs_client.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    logger.info("purge_sqs_queue: queue drained")
```

- [ ] **Step 2: Verify imports work**

Run: `cd tests/parity && python -c "from conftest import *; print('OK')"`
Expected: "OK" (no import errors).

Note: This may require adding `tests/` to the Python path or ensuring `tests/test_examples/conftest.py` is importable. If imports fail, adjust to use `sys.path.insert()` or move shared helpers to a package.

- [ ] **Step 3: Commit**

```bash
git add tests/parity/conftest.py
git commit -m "feat(parity): add test harness with SF execution, trace comparison, data seeding"
```

---

## Task 11: ETL Parity Test

**Files:**
- Create: `tests/parity/test-01-etl/test_etl_parity.py`

- [ ] **Step 1: Create the ETL parity test**

This test deploys the ETL infrastructure, seeds S3 with input data, runs the SF version, resets, runs the RSF version, then compares outputs and traces.

The implementer should follow the pattern from `tests/test_examples/test_order_processing.py`:
- Class-scoped deployment fixture
- `make_execution_id()` for unique names
- Invoke SF via `start_sf_execution()`, poll via `poll_sf_execution()`
- Invoke RSF via `lambda_client.invoke(FunctionName=alias_arn, InvocationType="Event", DurableExecutionName=exec_id)`
- Poll RSF via `poll_execution()`
- Compare S3 outputs (ignore `processed_at` field since timestamps will differ)
- Compare execution traces (state visit order)

Test methods:
- `test_sf_execution_succeeds` — SF reaches SUCCEEDED
- `test_rsf_execution_succeeds` — RSF reaches SUCCEEDED
- `test_output_parity` — S3 outputs match (ignoring timestamps)
- `test_trace_parity` — state visit sequences match

- [ ] **Step 2: Commit**

```bash
git add tests/parity/test-01-etl/test_etl_parity.py
git commit -m "feat(parity): add ETL parity test (S3 read → Map transform → S3 write)"
```

---

## Task 12: SQS Collector Parity Test

**Files:**
- Create: `tests/parity/test-02-sqs-collector/test_sqs_collector_parity.py`

- [ ] **Step 1: Create the SQS collector parity test**

This is the long-running test (~3 min). Key differences from ETL:
- Sends 10 SQS messages staggered over ~90s in a background thread
- Starts the workflow immediately (it polls for messages)
- Uses 5 min timeout
- After each workflow completes, verifies queue is empty
- Resets by purging queue and re-sending messages between SF and RSF runs
- Compares S3 output arrays (both should contain all 10 messages, order may differ — use set comparison on message content)
- Trace comparison: both should visit the same states, but the number of PollSQS/Wait loops may differ slightly due to timing — compare that both reach WriteToS3 and DeleteMessages

- [ ] **Step 2: Commit**

```bash
git add tests/parity/test-02-sqs-collector/test_sqs_collector_parity.py
git commit -m "feat(parity): add SQS collector parity test (long-running polling loop)"
```

---

## Task 13: Choice Routing Parity Test

**Files:**
- Create: `tests/parity/test-03-choice-routing/test_choice_routing_parity.py`

- [ ] **Step 1: Create the choice routing parity test**

This test runs twice — once with CSV config, once with JSON config. For each format:
- Seed config file + source data to S3
- Run SF, verify output at `sf/choice-routing/{format}/result.json`
- Reset, run RSF, verify output at `rsf/choice-routing/{format}/result.json`
- Compare outputs and traces

Additional test: verify Fail path — send a config with `format: "xml"` and verify both SF and RSF reach the HandleUnknownFormat Fail state.

Test methods:
- `test_csv_sf_succeeds`
- `test_csv_rsf_succeeds`
- `test_csv_output_parity`
- `test_json_sf_succeeds`
- `test_json_rsf_succeeds`
- `test_json_output_parity`
- `test_unknown_format_fails` (both SF and RSF)
- `test_trace_parity_csv`
- `test_trace_parity_json`

- [ ] **Step 2: Commit**

```bash
git add tests/parity/test-03-choice-routing/test_choice_routing_parity.py
git commit -m "feat(parity): add choice routing parity test (CSV vs JSON branching)"
```

---

## Task 14: Local Validation

**Files:** None (validation only)

- [ ] **Step 1: Verify all handler imports work**

```bash
cd tests/parity
python -c "from handlers.common.s3_utils import read_json_from_s3, write_json_to_s3; print('s3_utils OK')"
python -c "from handlers.common.sqs_utils import poll_sqs, delete_messages; print('sqs_utils OK')"
python -c "from handlers.etl.transform import transform_record; print('transform OK')"
python -c "from handlers.choice_routing.process_csv import process_csv; print('process_csv OK')"
python -c "from handlers.choice_routing.process_json import process_json; print('process_json OK')"
```

- [ ] **Step 2: Verify pure logic functions work**

```bash
python -c "
from handlers.etl.transform import transform_record
result = transform_record({'name': 'alice', 'age': 30})
assert result['name'] == 'ALICE'
assert 'processed_at' in result
print('transform_record: PASS')
"

python -c "
from handlers.choice_routing.process_csv import process_csv
result = process_csv('name,age\nalice,30\nbob,25')
assert len(result) == 2
assert result[0]['name'] == 'alice'
print('process_csv: PASS')
"

python -c "
from handlers.choice_routing.process_json import process_json
result = process_json([{'Name': 'Alice', 'Age': 30}])
assert result[0]['name'] == 'Alice'
assert result[0]['validated'] is True
print('process_json: PASS')
"
```

- [ ] **Step 3: Verify all Terraform modules validate**

```bash
for dir in shared test-01-etl test-02-sqs-collector test-03-choice-routing; do
  echo "Validating $dir..."
  cd tests/parity/$dir/terraform && terraform init -backend=false && terraform validate && cd ../../../..
done
```

- [ ] **Step 4: Commit any fixes**

If any validation issues found, fix and commit.

---

## Task 15: Integration Test Run

**Files:** None (execution only)

This task deploys everything to AWS and runs the full parity test suite. Requires AWS credentials for the `adfs` profile.

- [ ] **Step 1: Run the full parity test suite**

```bash
AWS_PROFILE=adfs AWS_REGION=us-east-2 pytest tests/parity/ -v -m parity --timeout=600
```

Expected: All tests pass. SF and RSF produce the same outputs for all 3 workflows.

- [ ] **Step 2: Verify cleanup**

After tests complete, verify no orphaned resources remain:
```bash
aws s3 ls | grep rsf-parity
aws sqs list-queues --queue-name-prefix rsf-parity
aws stepfunctions list-state-machines | grep parity
aws lambda list-functions | grep parity
```

Expected: No resources found (all cleaned up by terraform destroy).

- [ ] **Step 3: Commit any fixes from the integration run**

If any tests needed adjustment after running against real AWS, commit the fixes.
