# RSF — Replacement for Step Functions

A complete Python toolkit for defining, visualizing, generating, deploying, and debugging AWS Lambda Durable Functions workflows — with full AWS Step Functions feature parity.

## What is RSF?

RSF replaces AWS Step Functions with a local-first developer experience built on [AWS Lambda Durable Functions](https://aws.amazon.com/blogs/compute/introducing-aws-lambda-durable-functions/) (launched at re:Invent 2025). Define workflows in YAML, generate deployment-ready Python code, and inspect executions with a visual debugger — no hosted orchestration service required.

```yaml
rsf_version: "1.0"
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    Next: NotifyCustomer
  NotifyCustomer:
    Type: Task
    End: true
```

## Features

- **YAML/JSON DSL** — All 8 ASL state types, 39 comparison operators, 18 intrinsic functions, 5-stage I/O pipeline
- **Python Code Generation** — Lambda Durable Functions SDK code from your workflow definition, with handler stubs that are never overwritten
- **Terraform Generation** — Complete Lambda + IAM + CloudWatch infrastructure with auto-derived permissions
- **ASL Importer** — Migrate existing Step Functions workflows to RSF in minutes
- **Visual Graph Editor** — React-based editor with bidirectional YAML/graph sync and ELK auto-layout
- **Execution Inspector** — Time machine scrubbing, live SSE updates, structural JSON diffs
- **CLI Toolchain** — `rsf init`, `rsf generate`, `rsf validate`, `rsf deploy`, `rsf import`, `rsf ui`, `rsf inspect`

## Quickstart

### Install

```bash
pip install rsf
```

### Create a project

```bash
rsf init my-workflow
cd my-workflow
```

This creates a `workflow.yaml` and project scaffolding.

### Define your workflow

Edit `workflow.yaml`:

```yaml
rsf_version: "1.0"
Comment: "Order processing workflow"
StartAt: ValidateOrder
States:
  ValidateOrder:
    Type: Task
    Next: ProcessPayment
  ProcessPayment:
    Type: Task
    Retry:
      - ErrorEquals: ["PaymentError"]
        MaxAttempts: 3
        BackoffRate: 2.0
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: HandleFailure
    Next: SendConfirmation
  SendConfirmation:
    Type: Task
    End: true
  HandleFailure:
    Type: Fail
    Error: "PaymentFailed"
    Cause: "Payment processing failed"
```

### Generate code

```bash
rsf generate
```

This produces:
- `orchestrator.py` — Lambda Durable Functions orchestrator (regenerated on each run)
- `handlers/validate_order.py` — Handler stub (created once, never overwritten)
- `handlers/process_payment.py` — Handler stub
- `handlers/send_confirmation.py` — Handler stub

### Add business logic

```python
# handlers/validate_order.py
from rsf.registry import state

@state("ValidateOrder")
def handle(event, context):
    order = event["order"]
    if order["total"] <= 0:
        raise ValueError("Invalid order total")
    return {"validated": True, "orderId": order["id"]}
```

### Generate Terraform

```bash
rsf generate --terraform
```

Produces a complete Terraform module: `main.tf`, `variables.tf`, `iam.tf`, `outputs.tf`, `cloudwatch.tf`, `backend.tf`.

### Deploy

```bash
rsf deploy
```

### Inspect executions

```bash
rsf inspect
```

Opens the web-based execution inspector with time machine scrubbing.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                    RSF CLI                        │
│  init · generate · validate · deploy · import    │
│  ui · inspect                                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ DSL Core │  │ Code Gen │  │ Terraform│      │
│  │ Pydantic │  │  Jinja2  │  │   HCL    │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   ASL    │  │  Graph   │  │Inspector │      │
│  │ Importer │  │  Editor  │  │  + SSE   │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
├──────────────────────────────────────────────────┤
│              React UI (Vite + xyflow)            │
│        Graph Editor  ·  Execution Inspector      │
└──────────────────────────────────────────────────┘
```

## Documentation

Full documentation is available at the [docs site](docs/):

- [Tutorial](docs/tutorial.md) — From install through deploy and inspect
- [DSL Reference](docs/reference/dsl.md) — Complete field reference for all state types
- [State Types Guide](docs/reference/state-types.md) — Detailed examples with YAML + Python
- [Migration Guide](docs/migration-guide.md) — Import existing Step Functions workflows

## Technical Stack

| Layer | Technology |
|-------|-----------|
| DSL Models | Pydantic v2 (discriminated unions) |
| Code Generation | Jinja2 templates |
| Infrastructure | Terraform HCL generation |
| CLI | Typer + Rich |
| Web Backend | FastAPI (REST, WebSocket, SSE) |
| React UI | React 19 + @xyflow/react + Zustand + Monaco Editor |
| Graph Layout | ELK.js (Sugiyama algorithm) |
| Testing | pytest (441+ tests) + vitest (52 tests) |

## Requirements

- Python 3.12+ (SDK requires 3.13+)
- Node.js 18+ (for UI development)
- AWS account with Lambda Durable Functions enabled (for deployment)

## Development

```bash
# Clone and install
git clone https://github.com/your-org/rsf-python.git
cd rsf-python
pip install -e ".[dev]"

# Run tests
pytest

# Run UI tests
cd ui && npm test

# Start dev server (graph editor + inspector)
rsf ui --dev
```

## License

Apache-2.0
