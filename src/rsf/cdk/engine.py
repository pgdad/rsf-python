"""Jinja2 template engine for CDK Python code generation.

Uses standard Jinja2 delimiters since CDK templates produce Python code,
which doesn't conflict with {{ }} syntax (unlike HCL's ${} interpolation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_cdk_environment() -> Environment:
    """Create a Jinja2 environment with standard delimiters for CDK templates."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )


def render_cdk_template(template_name: str, **kwargs: Any) -> str:
    """Render a CDK template with the given context variables."""
    env = create_cdk_environment()
    template = env.get_template(template_name)
    return template.render(**kwargs)
