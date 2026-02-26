"""RSF init subcommand — scaffold a new RSF project."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console

console = Console()

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _render_template(template_name: str, **kwargs: str) -> str:
    """Read a template file and render it with Jinja2."""
    template_path = _TEMPLATES_DIR / template_name
    template_text = template_path.read_text(encoding="utf-8")
    if template_name.endswith(".j2"):
        return Template(template_text).render(**kwargs)
    return template_text


def init(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
) -> None:
    """Scaffold a new RSF project directory with workflow, handlers, and tests."""
    project_dir = Path.cwd() / project_name

    # Guard: refuse to overwrite an existing project
    if (project_dir / "workflow.yaml").exists():
        console.print(
            f"[red]Error:[/red] '{project_name}/workflow.yaml' already exists. "
            "Refusing to overwrite an existing project."
        )
        raise typer.Exit(code=1)

    # Create project directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    handlers_dir = project_dir / "handlers"
    handlers_dir.mkdir(exist_ok=True)
    tests_dir = project_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    created_files: list[str] = []

    # workflow.yaml — copy static template
    workflow_dest = project_dir / "workflow.yaml"
    shutil.copy2(_TEMPLATES_DIR / "workflow.yaml", workflow_dest)
    created_files.append("workflow.yaml")

    # handlers/__init__.py — empty
    handlers_init = handlers_dir / "__init__.py"
    handlers_init.write_text("", encoding="utf-8")
    created_files.append("handlers/__init__.py")

    # handlers/example_handler.py — static template
    handler_dest = handlers_dir / "example_handler.py"
    shutil.copy2(_TEMPLATES_DIR / "handler_example.py", handler_dest)
    created_files.append("handlers/example_handler.py")

    # pyproject.toml — rendered Jinja2 template
    pyproject_dest = project_dir / "pyproject.toml"
    pyproject_content = _render_template("pyproject.toml.j2", project_name=project_name)
    pyproject_dest.write_text(pyproject_content, encoding="utf-8")
    created_files.append("pyproject.toml")

    # .gitignore — static template (renamed from 'gitignore')
    gitignore_dest = project_dir / ".gitignore"
    shutil.copy2(_TEMPLATES_DIR / "gitignore", gitignore_dest)
    created_files.append(".gitignore")

    # tests/__init__.py — empty
    tests_init = tests_dir / "__init__.py"
    tests_init.write_text("", encoding="utf-8")
    created_files.append("tests/__init__.py")

    # tests/test_example.py — static template
    test_dest = tests_dir / "test_example.py"
    shutil.copy2(_TEMPLATES_DIR / "test_example.py", test_dest)
    created_files.append("tests/test_example.py")

    # Success summary
    console.print(f"\n[bold green]Created project:[/bold green] {project_name}/\n")
    for filename in created_files:
        console.print(f"  [dim]+[/dim] {project_name}/{filename}")
    console.print(
        f"\n[bold]Next steps:[/bold]\n"
        f"  cd {project_name}\n"
        f"  Edit workflow.yaml to define your state machine\n"
        f"  Edit handlers/example_handler.py to implement your logic"
    )
