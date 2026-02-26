---
status: complete
phase: 12-cli-toolchain
source: [12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md]
started: 2026-02-26T15:00:00Z
updated: 2026-02-26T15:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. rsf --version
expected: Running `rsf --version` prints the RSF version string (e.g., "rsf 0.1.0" or similar)
result: pass

### 2. rsf --help shows all subcommands
expected: Running `rsf --help` lists all 7 subcommands: init, validate, generate, deploy, import, ui, inspect
result: pass

### 3. rsf init scaffolds a project
expected: Running `rsf init my-project` creates a `my-project/` directory containing workflow.yaml, handlers/ directory, pyproject.toml, .gitignore, and tests/ directory
result: pass

### 4. rsf init duplicate guard
expected: Running `rsf init my-project` again in the same location (where my-project/ already has workflow.yaml) exits with an error instead of overwriting
result: pass

### 5. rsf validate on valid workflow
expected: Running `rsf validate workflow.yaml` on a valid workflow file prints a success message and exits with code 0
result: pass

### 6. rsf validate on broken workflow
expected: Running `rsf validate` on a YAML file with errors (e.g., missing required fields or dangling Next references) prints field-path-specific error messages and exits with code 1
result: pass

### 7. rsf generate produces code
expected: Running `rsf generate workflow.yaml` on a valid workflow produces an orchestrator.py file and handler stub files in a handlers/ directory, with a Rich summary showing created files
result: pass

### 8. rsf deploy missing terraform
expected: Running `rsf deploy` when `terraform` binary is not on PATH prints a clear error message mentioning terraform installation (not a stack trace)
result: pass

### 9. rsf import converts ASL JSON
expected: Running `rsf import <asl-file>.json` converts the ASL JSON to a workflow.yaml file and generates handler stubs; malformed JSON shows a clean error message
result: pass

### 10. rsf ui launches editor
expected: Running `rsf ui` starts the graph editor FastAPI server on port 8765 (or `--port <N>`) and attempts to open a browser. Ctrl+C stops it cleanly without a traceback
result: skipped
reason: User deferred server launch tests

### 11. rsf inspect launches inspector
expected: Running `rsf inspect --arn <any-arn>` starts the inspector server. Running without --arn and no terraform state shows a clear error about ARN discovery
result: skipped
reason: User deferred server launch tests

## Summary

total: 11
passed: 9
issues: 0
pending: 0
skipped: 2

## Gaps

[none yet]
