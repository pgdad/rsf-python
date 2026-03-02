---
plan: 46-02
status: complete
completed: 2026-03-02
requirements_completed: [UI-02]
---

# Plan 46-02: Schema Export CLI + SchemaStore — Summary

## What was built
`rsf schema export` CLI command that generates a comprehensive JSON Schema from the Pydantic DSL model covering all v2.0 fields, with bundled schema file and SchemaStore catalog entry ready for publication.

## Key files

### Created
- src/rsf/cli/schema_cmd.py — CLI command with --output and --stdout options
- schemas/rsf-workflow.json — Bundled JSON Schema (Draft 2020-12) with $id
- schemas/schemastore-catalog-entry.json — Ready-to-submit SchemaStore catalog entry
- tests/test_schema/__init__.py — Test package init
- tests/test_schema/test_schema_export.py — 15 tests covering schema gen and CLI

### Modified
- src/rsf/schema/generate.py — Added $id, updated description for v2.0 coverage
- src/rsf/cli/main.py — Registered schema command

## Self-Check: PASSED
- [x] generate_json_schema() includes $schema, $id, title, description
- [x] Schema covers all v2.0 DSL fields (triggers, sub_workflows, dynamodb_tables, alarms, dead_letter_queue, TimeoutSeconds)
- [x] $id uses GitHub raw URL format
- [x] rsf schema export creates file with default name
- [x] --output flag writes to custom path
- [x] --stdout prints valid JSON to stdout
- [x] SchemaStore catalog entry valid with workflow.yaml fileMatch
- [x] All 14 tests pass (1 skipped: jsonschema meta-validation)
- [x] No regressions

## Deviations
- Meta-schema validation test skipped gracefully when jsonschema library not installed (optional dependency)
- "stages" not a top-level DSL field — multi-stage deploy uses --stage CLI flag, not a schema property
