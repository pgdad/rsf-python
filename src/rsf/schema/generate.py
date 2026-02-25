"""JSON Schema generation from Pydantic v2 models.

Generates Draft 2020-12 JSON Schema from the StateMachineDefinition model
using Pydantic's built-in model_json_schema().
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rsf.dsl import StateMachineDefinition


def generate_json_schema() -> dict[str, Any]:
    """Generate JSON Schema (Draft 2020-12) from the StateMachineDefinition model."""
    schema = StateMachineDefinition.model_json_schema(
        mode="serialization",
    )
    # Add $schema declaration
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "RSF Workflow Definition"
    schema["description"] = (
        "Schema for RSF (Replacement for Step Functions) workflow definitions. "
        "Supports all 8 ASL state types with full feature parity."
    )
    return schema


def write_json_schema(output_path: str | Path) -> Path:
    """Generate and write JSON Schema to a file.

    Args:
        output_path: Path to write the schema file.

    Returns:
        The path that was written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = generate_json_schema()
    output_path.write_text(
        json.dumps(schema, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
