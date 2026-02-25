"""YAML/JSON loading and Pydantic validation for RSF workflow definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from rsf.dsl import StateMachineDefinition


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON file and return the raw dict."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".json",):
        return json.loads(text)
    return yaml.safe_load(text)


def parse_yaml(text: str) -> dict[str, Any]:
    """Parse a YAML string and return the raw dict."""
    return yaml.safe_load(text)


def parse_definition(data: dict[str, Any]) -> StateMachineDefinition:
    """Parse a raw dict into a validated StateMachineDefinition."""
    return StateMachineDefinition.model_validate(data)


def load_definition(path: str | Path) -> StateMachineDefinition:
    """Load and parse a YAML/JSON workflow file into a StateMachineDefinition."""
    data = load_yaml(path)
    return parse_definition(data)
