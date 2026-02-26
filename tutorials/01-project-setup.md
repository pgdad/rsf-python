# Tutorial 1: Project Setup with `rsf init`

This tutorial walks you through scaffolding a new RSF project, exploring every generated file,
and running the example tests to confirm everything works.

## What You'll Learn

- How to create a new RSF project directory with `rsf init`
- What each generated file does and why it exists
- How to run the example tests that come with the project
- Where to go next (Tutorial 2: workflow validation)

---

## Prerequisites

Before starting, you need:

- Python 3.12 or newer
- pip
- RSF installed

Install RSF with pip:

```bash
pip install rsf
```

Verify the installation:

```bash
rsf --version
```

You should see output like `rsf 0.1.0`. If the command is not found, ensure your Python scripts
directory is on your `PATH`.

---

## Step 1: Create Your Project

Run `rsf init` with your project name as the only argument:

```bash
rsf init my-workflow
```

RSF creates a new directory named `my-workflow/` in the current working directory and populates
it with a complete starter project. You will see output like this:

```
Created project: my-workflow/

  + my-workflow/workflow.yaml
  + my-workflow/handlers/__init__.py
  + my-workflow/handlers/example_handler.py
  + my-workflow/pyproject.toml
  + my-workflow/.gitignore
  + my-workflow/tests/__init__.py
  + my-workflow/tests/test_example.py

Next steps:
  cd my-workflow
  Edit workflow.yaml to define your state machine
  Edit handlers/example_handler.py to implement your logic
```

> If you run `rsf init my-workflow` a second time in the same directory, RSF will refuse to
> overwrite your existing project. This prevents accidental data loss.

---

## Step 2: Explore the Project Structure

Navigate into the new directory:

```bash
cd my-workflow
```

The directory layout looks like this:

```
my-workflow/
├── workflow.yaml
├── pyproject.toml
├── .gitignore
├── handlers/
│   ├── __init__.py
│   └── example_handler.py
└── tests/
    ├── __init__.py
    └── test_example.py
```

The next section explains what every file does.

---

## Understanding Each File

### `workflow.yaml` — The Workflow Definition

```yaml
rsf_version: "1.0"
Comment: "A minimal RSF workflow — edit to define your state machine"
StartAt: HelloWorld

States:
  HelloWorld:
    Type: Pass
    Result:
      message: "Hello from RSF!"
    Next: Done

  Done:
    Type: Succeed
```

This file defines your state machine using the RSF DSL. The top-level fields are:

- `rsf_version` — the RSF schema version this workflow targets.
- `Comment` — a human-readable description of the workflow (optional but recommended).
- `StartAt` — the name of the first state to execute when the workflow runs.
- `States` — a map of every state in the machine.

The starter workflow has two states. `HelloWorld` is a `Pass` state: it injects a static
`Result` object into the execution data and then transitions to the next state. `Done` is a
`Succeed` state: it marks the execution as successfully complete and terminates the workflow.

This is the file you edit to design your own state machine. Tutorial 2 shows you how to
validate changes to this file before generating any code.

---

### `handlers/example_handler.py` — The Handler Code

```python
"""Example RSF handler using the @state decorator."""

from rsf.functions.decorators import state


@state("HelloWorld")
def hello_world(event: dict, context: dict) -> dict:
    """Handle the HelloWorld state.

    Args:
        event: The input event for this state.
        context: The Lambda execution context.

    Returns:
        The output to pass to the next state.
    """
    name = event.get("name", "World")
    return {"message": f"Hello, {name}!"}
```

This file contains the business logic for your workflow states. The `@state("HelloWorld")`
decorator registers the `hello_world` function as the handler for the state named `HelloWorld`
in `workflow.yaml`. When the orchestrator reaches that state at runtime, it calls this function.

The function signature mirrors the AWS Lambda handler signature: `event` carries the input data
for the current state, and `context` carries Lambda execution metadata. The return value becomes
the output passed to the next state.

This is where your business logic lives. Add more handler functions — each decorated with the
`@state` name of the corresponding workflow state — as you build out your workflow.

---

### `handlers/__init__.py` — Package Marker

This file is empty. It marks the `handlers/` directory as a Python package so that the
generated orchestrator code and your tests can import from it using `from handlers.example_handler import hello_world`.

---

### `pyproject.toml` — Python Project Metadata

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-workflow"
version = "0.1.0"
description = "An RSF workflow project"
requires-python = ">=3.12"
dependencies = [
    "rsf>=0.1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "rsf[dev]",
]

[tool.hatch.build.targets.wheel]
packages = ["handlers"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
```

This is the standard Python project configuration file. Key sections:

- `[build-system]` — uses `hatchling` to build the project as a Python package. This makes
  the `handlers` package installable via `pip install -e .`.
- `[project]` — declares `rsf` and `pyyaml` as runtime dependencies.
- `[project.optional-dependencies]` — the `dev` extras add `pytest` and the RSF development
  tools used during testing and code generation.
- `[tool.hatch.build.targets.wheel]` — tells hatchling to include the `handlers` package in
  the built wheel, so the generated Lambda deployment package contains your handler code.
- `[tool.pytest.ini_options]` — tells pytest to look for tests in the `tests/` directory.

> The `name` field is set to your project name automatically by `rsf init`. No manual editing
> is required.

---

### `.gitignore` — Standard Ignore Patterns

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.pyo
*.pyd
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/
.tox/
.venv/
venv/
env/
.env
.envrc

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Terraform
.terraform/
*.tfstate
*.tfstate.*
*.tfstate.backup
.terraform.lock.hcl

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

This file tells git which files and directories to exclude from version control. It covers
Python bytecode and virtual environment directories, testing caches and coverage reports,
Terraform state files (which often contain secrets and should never be committed), and common
IDE and operating system artefacts.

---

### `tests/test_example.py` — Example Tests

```python
"""Example tests for RSF handlers."""

import pytest

from handlers.example_handler import hello_world


def test_hello_world_default() -> None:
    """Handler returns default greeting when no name is provided."""
    result = hello_world({}, {})
    assert result == {"message": "Hello, World!"}


def test_hello_world_with_name() -> None:
    """Handler returns personalized greeting when name is provided."""
    result = hello_world({"name": "RSF"}, {})
    assert result == {"message": "Hello, RSF!"}
```

RSF handlers are plain Python functions, so they are straightforward to test. Each test calls
the handler function directly — no mocking, no Lambda runtime required. `test_hello_world_default`
verifies the fallback behaviour when no `name` key is present in the event. `test_hello_world_with_name`
verifies the personalized greeting path.

This pattern scales to any handler you write: import the function, call it with a dict, assert
the return value.

---

### `tests/__init__.py` — Package Marker

This file is empty. It marks `tests/` as a Python package, which is required for pytest to
discover and run the test files inside it when your project is installed as an editable package.

---

## Step 3: Run the Example Tests

Install the project in editable mode so that pytest can import from `handlers/`:

```bash
pip install -e ".[dev]"
```

Then run the tests:

```bash
pytest
```

You should see output like:

```
========================= test session starts ==========================
platform linux -- Python 3.12.x, pytest-7.x.x
collected 2 items

tests/test_example.py ..                                          [100%]

========================== 2 passed in 0.07s ===========================
```

Both tests pass, confirming that the example handler works correctly and that your Python
environment is set up properly.

---

## What's Next

You now have a working RSF project directory with a valid starter workflow, an example handler,
and passing tests.

**Tutorial 2: Workflow Validation with `rsf validate`** shows you how to validate `workflow.yaml`
before generating any code. The workflow created here is already valid, but Tutorial 2 teaches
you how to intentionally introduce an error and use the 3-stage error messages to locate and
fix problems quickly. This skill is essential before you move on to code generation in Tutorial 3.
