---
phase: 55
plan: 4
status: complete
---

# Plan 55-04 Summary: Export command deduplication via create_metadata

## What was built
Eliminated code duplication by replacing `_extract_infrastructure_from_definition()` in `export_cmd.py` with the canonical `create_metadata()` + `dataclasses.asdict()` from `providers/metadata.py`.

## Key changes
- Deleted entire `_extract_infrastructure_from_definition()` function (~90 lines)
- Replaced with `create_metadata(definition, workflow_name)` + `asdict(metadata)`
- Removed unused imports (`StateMachineDefinition`, `TaskState`)
- Updated all test imports and calls to use `create_metadata`
- SAM template output is identical (all 20 tests pass unchanged)

## Key files
- `src/rsf/cli/export_cmd.py` -- deduplicated extraction logic (-87 lines)
- `tests/test_cli/test_export.py` -- updated imports and calls (20 tests)

## Test results
20/20 tests pass

## Commits
- `feat(55-04): replace duplicate extraction in export with create_metadata`
