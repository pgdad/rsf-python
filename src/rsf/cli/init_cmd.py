"""RSF init subcommand — scaffold a new RSF project."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

import typer
from jinja2 import Template
from rich.console import Console

console = Console()

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Template descriptions for --template list output
_TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "api-gateway-crud": "REST API with DynamoDB CRUD operations via API Gateway",
    "s3-event-pipeline": "S3 event-driven pipeline with processing and notification states",
}


def _render_template(template_name: str, **kwargs: str) -> str:
    """Read a template file and render it with Jinja2."""
    template_path = _TEMPLATES_DIR / template_name
    template_text = template_path.read_text(encoding="utf-8")
    if template_name.endswith(".j2"):
        return Template(template_text).render(**kwargs)
    return template_text


def _get_available_templates() -> list[str]:
    """Return names of available template subdirectories containing a workflow.yaml."""
    return sorted(
        d.name
        for d in _TEMPLATES_DIR.iterdir()
        if d.is_dir() and (d / "workflow.yaml").exists()
    )


def _scaffold_from_template(template_name: str, project_name: str, project_dir: Path) -> list[str]:
    """Copy a named template subdirectory into the project directory.

    Handles Jinja2 rendering for .j2 files, renames gitignore to .gitignore,
    and preserves subdirectory structure.

    Returns:
        List of relative file paths created.
    """
    template_dir = _TEMPLATES_DIR / template_name
    created_files: list[str] = []

    for root, dirs, files in os.walk(template_dir):
        root_path = Path(root)
        relative_root = root_path.relative_to(template_dir)
        dest_root = project_dir / relative_root

        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        dest_root.mkdir(parents=True, exist_ok=True)

        for filename in sorted(files):
            src_file = root_path / filename
            if filename == "__pycache__":
                continue

            if filename.endswith(".j2"):
                # Render Jinja2 templates, strip .j2 extension
                dest_name = filename[:-3]
                dest_file = dest_root / dest_name
                template_text = src_file.read_text(encoding="utf-8")
                rendered = Template(template_text).render(project_name=project_name)
                dest_file.write_text(rendered, encoding="utf-8")
            elif filename == "gitignore":
                # Rename gitignore to .gitignore
                dest_file = dest_root / ".gitignore"
                dest_name = ".gitignore"
                shutil.copy2(src_file, dest_file)
            else:
                dest_file = dest_root / filename
                dest_name = filename
                shutil.copy2(src_file, dest_file)

            rel_path = str((relative_root / dest_name))
            created_files.append(rel_path)

    return created_files


def init(
    project_name: Optional[str] = typer.Argument(None, help="Name of the project to create"),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Template to scaffold from. Use 'list' to see available templates.",
    ),
) -> None:
    """Scaffold a new RSF project directory with workflow, handlers, and tests."""
    available_templates = _get_available_templates()

    # Handle --template list
    if template == "list":
        console.print("\n[bold]Available templates:[/bold]\n")
        for tpl_name in available_templates:
            desc = _TEMPLATE_DESCRIPTIONS.get(tpl_name, "No description available")
            console.print(f"  [cyan]{tpl_name}[/cyan] — {desc}")
        console.print(
            f"\n[bold]Usage:[/bold] rsf init --template <name> [project-name]\n"
        )
        return

    # Handle --template <name>
    if template is not None:
        if template not in available_templates:
            console.print(
                f"[red]Error:[/red] Unknown template '{template}'. "
                f"Available templates:"
            )
            for tpl_name in available_templates:
                desc = _TEMPLATE_DESCRIPTIONS.get(tpl_name, "")
                console.print(f"  [cyan]{tpl_name}[/cyan] — {desc}")
            raise typer.Exit(code=1)

        # Default project name to template name if not provided
        if project_name is None:
            project_name = template

        project_dir = Path.cwd() / project_name

        # Guard: refuse to overwrite
        if (project_dir / "workflow.yaml").exists():
            console.print(
                f"[red]Error:[/red] '{project_name}/workflow.yaml' already exists. "
                "Refusing to overwrite an existing project."
            )
            raise typer.Exit(code=1)

        created_files = _scaffold_from_template(template, project_name, project_dir)

        console.print(
            f"\n[bold green]Created project from template "
            f"[cyan]{template}[/cyan]:[/bold green] {project_name}/\n"
        )
        for filename in created_files:
            console.print(f"  [dim]+[/dim] {project_name}/{filename}")
        console.print(
            f"\n[bold]Next steps:[/bold]\n"
            f"  cd {project_name}\n"
            f"  rsf validate          # Validate the workflow\n"
            f"  rsf generate          # Generate orchestrator code\n"
            f"  rsf deploy            # Deploy to AWS"
        )
        return

    # Default path: no --template, use HelloWorld scaffold
    if project_name is None:
        console.print(
            "[red]Error:[/red] Please provide a project name.\n"
            "  Usage: rsf init <project-name>\n"
            "  Or:    rsf init --template <name> [project-name]"
        )
        raise typer.Exit(code=1)

    project_dir = Path.cwd() / project_name

    # Guard: refuse to overwrite an existing project
    if (project_dir / "workflow.yaml").exists():
        console.print(
            f"[red]Error:[/red] '{project_name}/workflow.yaml' already exists. "
            "Refusing to overwrite an existing project."
        )
        raise typer.Exit(code=1)

    # Create project directory structure matching Terraform template expectations:
    #   project/
    #     workflow.yaml
    #     src/handlers/          ← user handler code
    #     src/generated/         ← rsf generate output (orchestrator.py)
    #     terraform/             ← rsf deploy output
    #     tests/
    project_dir.mkdir(parents=True, exist_ok=True)
    src_dir = project_dir / "src"
    src_dir.mkdir(exist_ok=True)
    handlers_dir = src_dir / "handlers"
    handlers_dir.mkdir(exist_ok=True)
    generated_dir = src_dir / "generated"
    generated_dir.mkdir(exist_ok=True)
    tests_dir = project_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    created_files: list[str] = []

    # workflow.yaml — copy template with project name substituted into Comment
    workflow_dest = project_dir / "workflow.yaml"
    template_text = (_TEMPLATES_DIR / "workflow.yaml").read_text(encoding="utf-8")
    workflow_dest.write_text(
        template_text.replace(
            "A minimal RSF workflow — edit to define your state machine",
            project_name,
        ),
        encoding="utf-8",
    )
    created_files.append("workflow.yaml")

    # src/handlers/__init__.py — empty
    handlers_init = handlers_dir / "__init__.py"
    handlers_init.write_text("", encoding="utf-8")
    created_files.append("src/handlers/__init__.py")

    # src/handlers/example_handler.py — static template
    handler_dest = handlers_dir / "example_handler.py"
    shutil.copy2(_TEMPLATES_DIR / "handler_example.py", handler_dest)
    created_files.append("src/handlers/example_handler.py")

    # src/generated/__init__.py — empty (needed for Python imports)
    generated_init = generated_dir / "__init__.py"
    generated_init.write_text("", encoding="utf-8")
    created_files.append("src/generated/__init__.py")

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
