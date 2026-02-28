"""Tests for YAML/JSON parsing and schema generation."""

import json

import yaml

from rsf.dsl.parser import load_definition, parse_definition, parse_yaml
from rsf.schema.generate import generate_json_schema, write_json_schema


class TestYAMLParsing:
    def test_parse_yaml_string(self):
        yaml_str = """
StartAt: A
States:
  A:
    Type: Succeed
"""
        data = parse_yaml(yaml_str)
        sm = parse_definition(data)
        assert sm.start_at == "A"

    def test_load_yaml_file(self, tmp_path):
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text(
            yaml.dump(
                {
                    "StartAt": "DoWork",
                    "States": {
                        "DoWork": {"Type": "Task", "Next": "Done"},
                        "Done": {"Type": "Succeed"},
                    },
                }
            )
        )
        sm = load_definition(workflow)
        assert sm.start_at == "DoWork"
        assert len(sm.states) == 2

    def test_load_json_file(self, tmp_path):
        workflow = tmp_path / "workflow.json"
        workflow.write_text(
            json.dumps(
                {
                    "StartAt": "A",
                    "States": {"A": {"Type": "Succeed"}},
                }
            )
        )
        sm = load_definition(workflow)
        assert sm.start_at == "A"


class TestJSONSchema:
    def test_generate(self):
        schema = generate_json_schema()
        assert "$schema" in schema
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "properties" in schema

    def test_write_schema(self, tmp_path):
        path = write_json_schema(tmp_path / "schema.json")
        assert path.exists()
        schema = json.loads(path.read_text())
        assert "properties" in schema
