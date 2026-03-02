---
phase: 51-provider-interface-and-metadata-foundation
plan: 03
status: complete
completed: "2026-03-02"
---

# Plan 51-03 Summary: Metadata Transports

## What Was Built
Three metadata transport mechanisms for delivering WorkflowMetadata to external provider commands: FileTransport (JSON file with mode 0600), EnvTransport (RSF_* env vars), and ArgsTransport (CLI arg templates with {placeholder} substitution).

## Key Files

### Created
- `src/rsf/providers/transports.py` — MetadataTransport ABC + FileTransport, EnvTransport, ArgsTransport
- `tests/test_providers/test_transports.py` — 28 tests for all transport mechanisms

### Modified
- `src/rsf/providers/__init__.py` — Added exports for WorkflowMetadata, create_metadata, and all transport types

## Test Results
28/28 transport tests passing. 76/76 total provider suite passing.

## Decisions Made
- FileTransport uses tempfile.mkstemp() for atomic file creation
- ArgsTransport validates at construction (not at prepare time) per locked decision
- _VALID_PLACEHOLDERS includes all WorkflowMetadata fields + "metadata_file"
- ArgsTransport splits formatted templates on whitespace to produce arg lists
- EnvTransport converts None stage to empty string

## Self-Check: PASSED
- [x] FileTransport writes JSON file with mode 0600, RSF_METADATA_FILE env var
- [x] FileTransport auto-cleans temp file, safe for double cleanup
- [x] EnvTransport sets RSF_WORKFLOW_NAME, RSF_STAGE, RSF_METADATA_JSON
- [x] ArgsTransport substitutes {placeholders} from WorkflowMetadata fields
- [x] ArgsTransport validates templates at construction — rejects invalid and unsafe placeholders
- [x] All 76 provider tests pass
