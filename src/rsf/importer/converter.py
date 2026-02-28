"""ASL JSON to RSF YAML converter.

Pipeline: ASL JSON file → parse_asl_json() → convert_asl_to_rsf() → emit_yaml()

Conversion rules:
1. Inject rsf_version: "1.0" at root
2. Reject Resource field with guidance to use @state decorators
3. Strip Fail state I/O fields (ASL allows them, RSF extra=forbid rejects them)
4. Rename legacy Iterator → ItemProcessor
5. Warn on distributed Map fields (ItemReader, ItemBatcher, ResultWriter)
6. Recursive conversion for Parallel branches and Map ItemProcessor
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ImportWarning:
    """A warning or error encountered during ASL import."""

    path: str
    field: str
    message: str
    severity: str = "warning"  # "warning" or "error"


@dataclass
class ImportResult:
    """Result of an ASL import operation."""

    rsf_dict: dict[str, Any]
    yaml_text: str
    warnings: list[ImportWarning] = field(default_factory=list)
    task_state_names: list[str] = field(default_factory=list)


# Fail state I/O fields that ASL allows but RSF rejects
_FAIL_IO_FIELDS = {
    "InputPath",
    "OutputPath",
    "Parameters",
    "ResultSelector",
    "ResultPath",
    "Assign",
    "Output",
}

# Distributed Map fields that RSF does not support
_DISTRIBUTED_MAP_FIELDS = {"ItemReader", "ItemBatcher", "ResultWriter"}


def parse_asl_json(source: str | Path) -> dict[str, Any]:
    """Parse an ASL JSON file or string into a dict.

    Args:
        source: Path to a JSON file, or a JSON string.

    Returns:
        The parsed ASL definition dict.

    Raises:
        ValueError: If the JSON is malformed.
    """
    if isinstance(source, Path) or (isinstance(source, str) and not source.strip().startswith(("{", "["))):
        path = Path(source)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise ValueError(f"ASL file not found: {path}")
        except OSError as e:
            raise ValueError(f"Cannot read ASL file: {e}")
    else:
        text = source

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError("ASL definition must be a JSON object")

    return data


def convert_asl_to_rsf(
    asl: dict[str, Any],
) -> ImportResult:
    """Convert an ASL definition dict to RSF format.

    Args:
        asl: The parsed ASL definition.

    Returns:
        ImportResult with the converted dict, YAML text, warnings, and task names.
    """
    warnings: list[ImportWarning] = []
    task_names: list[str] = []

    rsf = _convert_root(asl, warnings, task_names)
    yaml_text = emit_yaml(rsf)

    return ImportResult(
        rsf_dict=rsf,
        yaml_text=yaml_text,
        warnings=warnings,
        task_state_names=task_names,
    )


def import_asl(
    source: str | Path,
    output_path: Path | None = None,
    handlers_dir: Path | None = None,
) -> ImportResult:
    """Full import pipeline: parse → convert → emit YAML → generate handler stubs.

    Args:
        source: Path to ASL JSON file or JSON string.
        output_path: Where to write the RSF YAML (None = don't write).
        handlers_dir: Where to write handler stubs (None = don't write).

    Returns:
        ImportResult with converted data and metadata.
    """
    asl = parse_asl_json(source)
    result = convert_asl_to_rsf(asl)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.yaml_text, encoding="utf-8")

    if handlers_dir is not None and result.task_state_names:
        _generate_handler_stubs(result.task_state_names, handlers_dir)

    return result


def emit_yaml(data: dict[str, Any]) -> str:
    """Emit clean YAML from a converted RSF dict.

    Uses block style for readability and sorts keys for deterministic output.
    """
    return yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )


def _convert_root(
    asl: dict[str, Any],
    warnings: list[ImportWarning],
    task_names: list[str],
) -> dict[str, Any]:
    """Convert the root ASL definition to RSF format."""
    rsf: dict[str, Any] = {"rsf_version": "1.0"}

    # Copy top-level fields
    if "Comment" in asl:
        rsf["Comment"] = asl["Comment"]

    if "StartAt" not in asl:
        raise ValueError("ASL definition missing required 'StartAt' field")
    rsf["StartAt"] = asl["StartAt"]

    if "States" not in asl:
        raise ValueError("ASL definition missing required 'States' field")

    rsf["States"] = _convert_states(asl["States"], "", warnings, task_names)

    # Optional fields
    if "Version" in asl:
        rsf["Version"] = asl["Version"]
    if "TimeoutSeconds" in asl:
        rsf["TimeoutSeconds"] = asl["TimeoutSeconds"]
    if "QueryLanguage" in asl:
        rsf["QueryLanguage"] = asl["QueryLanguage"]

    return rsf


def _convert_states(
    states: dict[str, Any],
    path: str,
    warnings: list[ImportWarning],
    task_names: list[str],
) -> dict[str, Any]:
    """Convert a states dict, applying all conversion rules."""
    converted: dict[str, Any] = {}
    for name, state_data in states.items():
        if not isinstance(state_data, dict):
            converted[name] = state_data
            continue
        state_path = f"{path}States.{name}" if path else f"States.{name}"
        converted[name] = _convert_state(name, state_data, state_path, warnings, task_names)
    return converted


def _convert_state(
    name: str,
    state: dict[str, Any],
    path: str,
    warnings: list[ImportWarning],
    task_names: list[str],
) -> dict[str, Any]:
    """Convert a single state, applying type-specific rules."""
    state = dict(state)  # Shallow copy
    state_type = state.get("Type", "")

    # Rule 2: Reject Resource field
    if "Resource" in state:
        warnings.append(
            ImportWarning(
                path=f"{path}.Resource",
                field="Resource",
                message=(
                    f"State '{name}' has a Resource field ('{state['Resource']}'). "
                    "RSF does not use Resource — use @state decorators to register handlers instead. "
                    "The Resource field has been removed."
                ),
                severity="warning",
            )
        )
        del state["Resource"]

    # Rule 3: Strip Fail state I/O fields
    if state_type == "Fail":
        for io_field in _FAIL_IO_FIELDS:
            if io_field in state:
                del state[io_field]

    # Rule 4: Rename legacy Iterator → ItemProcessor
    if state_type == "Map" and "Iterator" in state:
        state["ItemProcessor"] = state.pop("Iterator")
        warnings.append(
            ImportWarning(
                path=f"{path}.Iterator",
                field="Iterator",
                message=f"Renamed legacy 'Iterator' to 'ItemProcessor' in state '{name}'.",
                severity="warning",
            )
        )

    # Rule 5: Warn on distributed Map fields
    if state_type == "Map":
        for dist_field in _DISTRIBUTED_MAP_FIELDS:
            if dist_field in state:
                warnings.append(
                    ImportWarning(
                        path=f"{path}.{dist_field}",
                        field=dist_field,
                        message=(
                            f"Distributed Map field '{dist_field}' in state '{name}' "
                            "is not supported by RSF and has been removed."
                        ),
                        severity="warning",
                    )
                )
                del state[dist_field]

    # Collect Task state names for handler stub generation
    if state_type == "Task":
        task_names.append(name)

    # Rule 6: Recursive conversion for Parallel branches
    if state_type == "Parallel" and "Branches" in state:
        state["Branches"] = [
            _convert_branch(branch, f"{path}.Branches[{i}]", warnings, task_names)
            for i, branch in enumerate(state["Branches"])
        ]

    # Rule 6: Recursive conversion for Map ItemProcessor
    if state_type == "Map" and "ItemProcessor" in state:
        state["ItemProcessor"] = _convert_branch(state["ItemProcessor"], f"{path}.ItemProcessor", warnings, task_names)

    return state


def _convert_branch(
    branch: dict[str, Any],
    path: str,
    warnings: list[ImportWarning],
    task_names: list[str],
) -> dict[str, Any]:
    """Recursively convert a branch (Parallel branch or Map ItemProcessor)."""
    branch = dict(branch)  # Shallow copy
    if "States" in branch:
        branch["States"] = _convert_states(branch["States"], f"{path}.", warnings, task_names)
    return branch


def _generate_handler_stubs(
    task_names: list[str],
    handlers_dir: Path,
) -> list[Path]:
    """Generate handler stub files for Task states.

    Reuses the codegen handler stub renderer.
    """
    from rsf.codegen.generator import render_handler_stub, _to_snake_case

    handlers_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for name in task_names:
        handler_path = handlers_dir / f"{_to_snake_case(name)}.py"
        if not handler_path.exists():
            stub_code = render_handler_stub(name)
            handler_path.write_text(stub_code, encoding="utf-8")
            created.append(handler_path)

    return created
