"""Tests for the ASL importer."""

import json
from pathlib import Path

import pytest

from rsf.importer.converter import (
    ImportResult,
    ImportWarning,
    convert_asl_to_rsf,
    emit_yaml,
    import_asl,
    parse_asl_json,
)


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "asl"


class TestParseAslJson:
    def test_parse_file(self):
        data = parse_asl_json(FIXTURES_DIR / "simple_workflow.json")
        assert "StartAt" in data
        assert "States" in data

    def test_parse_string(self):
        asl_str = '{"StartAt": "Go", "States": {"Go": {"Type": "Succeed"}}}'
        data = parse_asl_json(asl_str)
        assert data["StartAt"] == "Go"

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError, match="Malformed JSON"):
            parse_asl_json("{invalid json")

    def test_non_object_raises(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            parse_asl_json("[1, 2, 3]")

    def test_file_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            parse_asl_json(Path("/nonexistent/file.json"))


class TestConvertAslToRsf:
    def test_injects_rsf_version(self):
        asl = {"StartAt": "Go", "States": {"Go": {"Type": "Succeed"}}}
        result = convert_asl_to_rsf(asl)
        assert result.rsf_dict["rsf_version"] == "1.0"

    def test_preserves_comment(self):
        asl = {"Comment": "My workflow", "StartAt": "Go", "States": {"Go": {"Type": "Succeed"}}}
        result = convert_asl_to_rsf(asl)
        assert result.rsf_dict["Comment"] == "My workflow"

    def test_preserves_start_at(self):
        asl = {"StartAt": "First", "States": {"First": {"Type": "Succeed"}}}
        result = convert_asl_to_rsf(asl)
        assert result.rsf_dict["StartAt"] == "First"

    def test_missing_start_at_raises(self):
        with pytest.raises(ValueError, match="StartAt"):
            convert_asl_to_rsf({"States": {"Go": {"Type": "Succeed"}}})

    def test_missing_states_raises(self):
        with pytest.raises(ValueError, match="States"):
            convert_asl_to_rsf({"StartAt": "Go"})


class TestResourceRejection:
    def test_resource_removed_with_warning(self):
        asl = {
            "StartAt": "Do",
            "States": {
                "Do": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:123:function:do",
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        assert "Resource" not in result.rsf_dict["States"]["Do"]
        assert any(w.field == "Resource" for w in result.warnings)

    def test_resource_warning_mentions_state_decorator(self):
        asl = {
            "StartAt": "Do",
            "States": {
                "Do": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:123:function:do",
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        resource_warnings = [w for w in result.warnings if w.field == "Resource"]
        assert len(resource_warnings) == 1
        assert "@state" in resource_warnings[0].message


class TestFailStateStrip:
    def test_fail_io_fields_stripped(self):
        asl = {
            "StartAt": "Boom",
            "States": {
                "Boom": {
                    "Type": "Fail",
                    "Error": "MyError",
                    "Cause": "Something broke",
                    "InputPath": "$.input",
                    "OutputPath": "$.output",
                    "Parameters": {"key": "val"},
                    "ResultSelector": {"key": "val"},
                    "ResultPath": "$.result",
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        fail_state = result.rsf_dict["States"]["Boom"]
        assert "InputPath" not in fail_state
        assert "OutputPath" not in fail_state
        assert "Parameters" not in fail_state
        assert "ResultSelector" not in fail_state
        assert "ResultPath" not in fail_state
        # Error and Cause should be preserved
        assert fail_state["Error"] == "MyError"
        assert fail_state["Cause"] == "Something broke"


class TestIteratorRename:
    def test_iterator_renamed_to_item_processor(self):
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "Iterator": {
                        "StartAt": "Sub",
                        "States": {"Sub": {"Type": "Task", "End": True}},
                    },
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        map_state = result.rsf_dict["States"]["MapIt"]
        assert "Iterator" not in map_state
        assert "ItemProcessor" in map_state
        assert any(w.field == "Iterator" for w in result.warnings)


class TestDistributedMapWarnings:
    def test_warns_on_item_reader(self):
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "ItemReader": {"ReaderConfig": {}},
                    "ItemProcessor": {"StartAt": "S", "States": {"S": {"Type": "Task", "End": True}}},
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        assert any(w.field == "ItemReader" for w in result.warnings)
        assert "ItemReader" not in result.rsf_dict["States"]["MapIt"]

    def test_warns_on_item_batcher(self):
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "ItemBatcher": {"MaxBatchSize": 10},
                    "ItemProcessor": {"StartAt": "S", "States": {"S": {"Type": "Task", "End": True}}},
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        assert any(w.field == "ItemBatcher" for w in result.warnings)

    def test_warns_on_result_writer(self):
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "ResultWriter": {"WriterConfig": {}},
                    "ItemProcessor": {"StartAt": "S", "States": {"S": {"Type": "Task", "End": True}}},
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        assert any(w.field == "ResultWriter" for w in result.warnings)


class TestRecursiveConversion:
    def test_parallel_branches_converted(self):
        asl = {
            "StartAt": "RunBoth",
            "States": {
                "RunBoth": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "A",
                            "States": {
                                "A": {"Type": "Task", "Resource": "arn:a", "End": True},
                            },
                        },
                        {
                            "StartAt": "B",
                            "States": {
                                "B": {"Type": "Task", "Resource": "arn:b", "End": True},
                            },
                        },
                    ],
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        branches = result.rsf_dict["States"]["RunBoth"]["Branches"]

        # Resource should be stripped from branch tasks
        assert "Resource" not in branches[0]["States"]["A"]
        assert "Resource" not in branches[1]["States"]["B"]

        # Task names should include branch tasks
        assert "A" in result.task_state_names
        assert "B" in result.task_state_names

    def test_map_item_processor_converted(self):
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "ItemProcessor": {
                        "StartAt": "Sub",
                        "States": {
                            "Sub": {"Type": "Task", "Resource": "arn:sub", "End": True},
                        },
                    },
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        sub = result.rsf_dict["States"]["MapIt"]["ItemProcessor"]["States"]["Sub"]
        assert "Resource" not in sub
        assert "Sub" in result.task_state_names

    def test_nested_parallel_in_map(self):
        """Deeply nested: Map containing Parallel containing Task."""
        asl = {
            "StartAt": "MapIt",
            "States": {
                "MapIt": {
                    "Type": "Map",
                    "ItemProcessor": {
                        "StartAt": "InnerParallel",
                        "States": {
                            "InnerParallel": {
                                "Type": "Parallel",
                                "Branches": [
                                    {
                                        "StartAt": "Deep",
                                        "States": {
                                            "Deep": {"Type": "Task", "Resource": "arn:deep", "End": True},
                                        },
                                    },
                                ],
                                "End": True,
                            },
                        },
                    },
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        deep = result.rsf_dict["States"]["MapIt"]["ItemProcessor"]["States"]["InnerParallel"]["Branches"][0]["States"][
            "Deep"
        ]
        assert "Resource" not in deep
        assert "Deep" in result.task_state_names


class TestEmitYaml:
    def test_produces_valid_yaml(self):
        data = {"rsf_version": "1.0", "StartAt": "Go", "States": {"Go": {"Type": "Succeed"}}}
        text = emit_yaml(data)
        parsed = __import__("yaml").safe_load(text)
        assert parsed["rsf_version"] == "1.0"

    def test_preserves_structure(self):
        data = {
            "rsf_version": "1.0",
            "StartAt": "Do",
            "States": {
                "Do": {"Type": "Task", "End": True},
            },
        }
        text = emit_yaml(data)
        parsed = __import__("yaml").safe_load(text)
        assert parsed["States"]["Do"]["Type"] == "Task"


class TestTaskStateCollection:
    def test_collects_all_task_states(self):
        asl = {
            "StartAt": "A",
            "States": {
                "A": {"Type": "Task", "Resource": "arn:a", "Next": "B"},
                "B": {"Type": "Task", "Resource": "arn:b", "Next": "C"},
                "C": {"Type": "Pass", "End": True},
            },
        }
        result = convert_asl_to_rsf(asl)
        assert result.task_state_names == ["A", "B"]

    def test_collects_from_branches(self):
        asl = {
            "StartAt": "Par",
            "States": {
                "Par": {
                    "Type": "Parallel",
                    "Branches": [
                        {"StartAt": "X", "States": {"X": {"Type": "Task", "Resource": "arn:x", "End": True}}},
                    ],
                    "End": True,
                },
            },
        }
        result = convert_asl_to_rsf(asl)
        assert "X" in result.task_state_names


class TestImportAsl:
    def test_full_pipeline_from_file(self, tmp_path):
        result = import_asl(
            FIXTURES_DIR / "simple_workflow.json",
            output_path=tmp_path / "workflow.yaml",
            handlers_dir=tmp_path / "handlers",
        )
        assert (tmp_path / "workflow.yaml").exists()
        assert result.rsf_dict["rsf_version"] == "1.0"
        assert "Resource" not in result.rsf_dict["States"]["ValidateOrder"]
        assert len(result.task_state_names) == 3  # ValidateOrder, HighValueApproval, ProcessOrder

    def test_handler_stubs_created(self, tmp_path):
        import_asl(
            FIXTURES_DIR / "simple_workflow.json",
            output_path=tmp_path / "workflow.yaml",
            handlers_dir=tmp_path / "handlers",
        )
        assert (tmp_path / "handlers" / "validate_order.py").exists()
        assert (tmp_path / "handlers" / "high_value_approval.py").exists()
        assert (tmp_path / "handlers" / "process_order.py").exists()

    def test_parallel_map_fixture(self, tmp_path):
        result = import_asl(
            FIXTURES_DIR / "parallel_map.json",
            output_path=tmp_path / "workflow.yaml",
            handlers_dir=tmp_path / "handlers",
        )
        # Iterator should be renamed
        assert "ItemProcessor" in result.rsf_dict["States"]["ProcessItems"]
        assert "Iterator" not in result.rsf_dict["States"]["ProcessItems"]
        # Task states from branches
        assert "BranchA" in result.task_state_names
        assert "BranchB" in result.task_state_names
        assert "MapTask" in result.task_state_names

    def test_imported_yaml_validates(self, tmp_path):
        """Imported YAML should parse and validate with RSF DSL."""
        import_asl(
            FIXTURES_DIR / "simple_workflow.json",
            output_path=tmp_path / "workflow.yaml",
        )
        from rsf.dsl.parser import load_definition
        from rsf.dsl.validator import validate_definition

        sm = load_definition(tmp_path / "workflow.yaml")
        errors = validate_definition(sm)
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_parallel_map_yaml_validates(self, tmp_path):
        """Parallel+Map imported YAML should parse and validate."""
        import_asl(
            FIXTURES_DIR / "parallel_map.json",
            output_path=tmp_path / "workflow.yaml",
        )
        from rsf.dsl.parser import load_definition
        from rsf.dsl.validator import validate_definition

        sm = load_definition(tmp_path / "workflow.yaml")
        errors = validate_definition(sm)
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"
