# RSF — Replacement for Step Functions

[![PyPI version](https://img.shields.io/pypi/v/rsf)](https://pypi.org/project/rsf/)
[![CI](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg)](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

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

## Screenshots

| Graph Editor | Execution Inspector |
|:---:|:---:|
| ![Graph Editor](https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/order-processing-graph.png) | ![Execution Inspector](https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/order-processing-inspector.png) |

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

```
Created project: my-workflow/

  + my-workflow/workflow.yaml
  + my-workflow/handlers/__init__.py
  + my-workflow/handlers/example_handler.py
  + my-workflow/pyproject.toml
  + my-workflow/.gitignore
  + my-workflow/tests/__init__.py
  + my-workflow/tests/test_example.py
```

Edit `workflow.yaml` to define your states, then generate code.

### Generate code

```bash
rsf generate
```

```
Generated: orchestrator.py
  Created: handlers/validate_order.py
  Created: handlers/process_payment.py
  Created: handlers/send_confirmation.py

Summary: orchestrator written, 3 handler(s) created, 0 skipped.
```

### Deploy

```bash
rsf deploy
```

```
Code generated: orchestrator.py + 3 handler(s) (0 skipped)
Terraform generated: 6 file(s) in terraform (0 skipped)

Running terraform init...
Running terraform apply...

Deploy complete
```

### Inspect executions

```bash
rsf inspect
```

Opens the execution inspector at http://localhost:8001

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

Full documentation is available at the [docs site](https://github.com/pgdad/rsf-python/tree/main/docs):

- [Tutorial](https://github.com/pgdad/rsf-python/blob/main/docs/tutorial.md) — From install through deploy and inspect
- [DSL Reference](https://github.com/pgdad/rsf-python/blob/main/docs/reference/dsl.md) — Complete field reference for all state types
- [State Types Guide](https://github.com/pgdad/rsf-python/blob/main/docs/reference/state-types.md) — Detailed examples with YAML + Python
- [Migration Guide](https://github.com/pgdad/rsf-python/blob/main/docs/migration-guide.md) — Import existing Step Functions workflows

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
git clone https://github.com/pgdad/rsf-python.git
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
