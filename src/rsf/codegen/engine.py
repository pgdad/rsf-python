"""Jinja2 template engine setup for RSF code generation.

Provides the configured Jinja2 environment, custom filters, and template rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


def topyrepr(value: Any) -> str:
    """Convert a value to its Python repr string.

    Critical for code generation:
    - True/False/None instead of true/false/null
    - Strings properly quoted
    - Recursive for dicts/lists
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        items = ", ".join(topyrepr(item) for item in value)
        return f"[{items}]"
    if isinstance(value, dict):
        items = ", ".join(
            f"{topyrepr(k)}: {topyrepr(v)}" for k, v in value.items()
        )
        return "{" + items + "}"
    return repr(value)


def create_environment() -> Environment:
    """Create a configured Jinja2 environment for Python code generation."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["topyrepr"] = topyrepr
    return env


def render_template(template_name: str, **kwargs: Any) -> str:
    """Render a template with the given context variables."""
    env = create_environment()
    template = env.get_template(template_name)
    return template.render(**kwargs)
