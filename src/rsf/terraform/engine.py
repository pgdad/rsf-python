"""Jinja2 template engine for HCL/Terraform generation.

Uses custom delimiters to avoid conflicts with Terraform's ${} interpolation:
- Variables: << var >> instead of {{ var }}
- Blocks: <% if %> instead of {% if %}
- Comments: <# note #> instead of {# note #}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_hcl_environment() -> Environment:
    """Create a Jinja2 environment with custom HCL-safe delimiters."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        variable_start_string="<<",
        variable_end_string=">>",
        block_start_string="<%",
        block_end_string="%>",
        comment_start_string="<#",
        comment_end_string="#>",
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )


def render_hcl_template(template_name: str, **kwargs: Any) -> str:
    """Render an HCL template with the given context variables."""
    env = create_hcl_environment()
    template = env.get_template(template_name)
    return template.render(**kwargs)
