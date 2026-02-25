# RSF — Replacement for Step Functions

RSF is a complete Python toolkit for defining, visualizing, generating, deploying, and debugging AWS Lambda Durable Functions workflows — with full AWS Step Functions feature parity.

## Why RSF?

AWS Step Functions is powerful but comes with trade-offs: a hosted service dependency, limited local development, and a JSON-heavy authoring experience. **AWS Lambda Durable Functions** (launched at re:Invent 2025) moves orchestration into your Lambda functions — but requires you to write the state management code yourself.

RSF bridges that gap. Define workflows in YAML (the same state types you already know from ASL), and RSF generates deployment-ready Python code, Terraform infrastructure, and gives you a visual editor and execution inspector.

## What you get

| Capability | Description |
|-----------|-------------|
| **YAML/JSON DSL** | All 8 ASL state types, 39 comparison operators, 18 intrinsic functions |
| **Code Generation** | Lambda Durable Functions SDK code with handler stubs |
| **Terraform Generation** | Lambda + IAM + CloudWatch with auto-derived permissions |
| **ASL Importer** | Migrate existing Step Functions workflows |
| **Graph Editor** | Visual editor with bidirectional YAML/graph sync |
| **Execution Inspector** | Time machine scrubbing, live updates, structural diffs |
| **CLI** | `rsf init`, `generate`, `validate`, `deploy`, `import`, `ui`, `inspect` |

## Quick example

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

```bash
rsf generate    # Produces orchestrator.py + handler stubs
rsf deploy      # Deploys via Terraform
rsf inspect     # Opens the visual debugger
```

## Getting started

Follow the [Tutorial](tutorial.md) to go from `pip install rsf` through deploying and inspecting your first workflow.

Already using Step Functions? See the [Migration Guide](migration-guide.md) to import your existing ASL JSON workflows.

## Requirements

- Python 3.12+ (Lambda Durable Functions SDK requires 3.13+)
- AWS account with Lambda Durable Functions enabled (for deployment)
