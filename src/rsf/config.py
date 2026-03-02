"""RSF project configuration -- rsf.toml loader and config resolution.

Loads provider configuration from rsf.toml files and resolves the
infrastructure configuration cascade: workflow YAML > rsf.toml > default.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from rsf.dsl.models import InfrastructureConfig, StateMachineDefinition


def load_project_config(directory: Path) -> InfrastructureConfig | None:
    """Load ``[infrastructure]`` from rsf.toml in the given directory.

    Looks for ``rsf.toml`` in ``directory`` (same directory as workflow YAML).
    No upward traversal, no git root lookup.

    Args:
        directory: Directory to search for rsf.toml.

    Returns:
        InfrastructureConfig if rsf.toml exists and has [infrastructure],
        None otherwise.

    Raises:
        pydantic.ValidationError: If [infrastructure] content is invalid.
    """
    toml_path = directory / "rsf.toml"
    if not toml_path.exists():
        return None
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    if "infrastructure" not in data:
        return None
    infra_data = data["infrastructure"]
    if infra_data is None:
        return None
    return InfrastructureConfig.model_validate(infra_data)


def resolve_infra_config(
    definition: StateMachineDefinition,
    workflow_dir: Path,
) -> InfrastructureConfig:
    """Resolve infrastructure config: YAML > rsf.toml > default.

    Priority cascade:
    1. Workflow YAML ``infrastructure:`` block (if present)
    2. rsf.toml ``[infrastructure]`` table (if file exists)
    3. Default InfrastructureConfig (provider="terraform")

    Args:
        definition: Parsed workflow definition (may have infrastructure field).
        workflow_dir: Directory containing the workflow YAML (and rsf.toml).

    Returns:
        Resolved InfrastructureConfig. Never None.
    """
    if definition.infrastructure is not None:
        return definition.infrastructure
    toml_config = load_project_config(workflow_dir)
    if toml_config is not None:
        return toml_config
    return InfrastructureConfig()
