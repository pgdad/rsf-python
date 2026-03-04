---
phase: 57-core-lambda-example
plan: 03
subsystem: infra
tags: [bash, terraform, rsf-toml, custom-provider, file-transport, jq, lambda, registry-modules]

# Dependency graph
requires:
  - phase: 57-core-lambda-example
    plan: 01
    provides: "--teardown CLI flag, image-processing workflow.yaml, 4 @state handlers"
  - phase: 57-core-lambda-example
    plan: 02
    provides: "all 5 Terraform files (main.tf, iam_durable.tf, variables.tf, outputs.tf, backend.tf)"
provides:
  - "examples/registry-modules-demo/deploy.sh — bash deploy/destroy script reading RSF_METADATA_FILE via jq"
  - "examples/registry-modules-demo/rsf.toml — CustomProvider configuration with args/teardown_args/metadata_transport"
  - "examples/registry-modules-demo/README.md — quick start, prerequisites, architecture, teardown instructions"
affects:
  - "Phase 59 (end-to-end deployment testing)"
  - "Phase 60 (tutorial documentation)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SCRIPT_DIR via BASH_SOURCE[0] — never rely on $PWD for portable script paths"
    - "jq alternative operator: .timeout_seconds // 86400 for null fallback in metadata extraction"
    - "zip -r with -x to exclude pycache before terraform apply"
    - "terraform output -raw alias_arn to capture and print alias ARN post-deploy"

key-files:
  created:
    - "examples/registry-modules-demo/deploy.sh"
    - "examples/registry-modules-demo/rsf.toml"
    - "examples/registry-modules-demo/README.md"
  modified: []

key-decisions:
  - "deploy.sh uses jq // alternative operator (not shell default ${:-}) for null fallback on timeout_seconds — matches jq semantics for absent keys"
  - "rsf.toml program field uses obvious /REPLACE/... placeholder so users cannot accidentally run without setting their path"
  - "README kept under 120 lines (118 lines) — example documentation, not tutorial (Phase 60)"

patterns-established:
  - "Pattern: custom-provider-script — set -euo pipefail + SCRIPT_DIR via BASH_SOURCE + jq metadata extraction + CMD dispatch case"
  - "Pattern: rsf.toml layout — [infrastructure] provider='custom' + [infrastructure.custom] program/args/teardown_args/metadata_transport"

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-04]

# Metrics
duration: 5min
completed: 2026-03-04
---

# Phase 57 Plan 03: Core Lambda Example Summary

**Bash deploy.sh reading RSF_METADATA_FILE via jq (workflow_name + timeout_seconds), zip src/generated/ + handlers/ into build/function.zip, terraform apply/destroy dispatch, alias ARN printed post-deploy — plus rsf.toml custom provider config and README quick start**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-04T13:50:17Z
- **Completed:** 2026-03-04T13:55:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `deploy.sh` with `set -euo pipefail`, SCRIPT_DIR computed via BASH_SOURCE, jq metadata extraction (workflow_name + timeout_seconds with null fallback via `//`), zip step (excludes pycache), terraform init + apply with -var flags, and post-deploy alias ARN print with sample `aws lambda invoke` command
- Created `rsf.toml` configuring CustomProvider with provider="custom", program placeholder, args=["deploy"], teardown_args=["destroy"], metadata_transport="file"
- Created `README.md` (118 lines) with architecture diagram, prerequisites, quick start (absolute path setup, chmod, rsf deploy, invoke, teardown), directory structure, and how-it-works flow

## Task Commits

Each task was committed atomically:

1. **Task 1: Create deploy.sh and rsf.toml** - `edd4d40` (feat)
2. **Task 2: Create README.md for the example** - `8cbb390` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `examples/registry-modules-demo/deploy.sh` - Bash deploy/destroy script: RSF_METADATA_FILE via jq, zip source+handlers, terraform apply with -var flags, alias ARN printed post-deploy; destroy runs terraform destroy
- `examples/registry-modules-demo/rsf.toml` - CustomProvider config: provider=custom, args=["deploy"], teardown_args=["destroy"], metadata_transport=file, placeholder program path
- `examples/registry-modules-demo/README.md` - Example documentation: overview, architecture diagram, prerequisites, quick start (6 steps including absolute path setup), directory structure, workflow description, how-it-works

## Decisions Made

- `deploy.sh` uses jq's `//` alternative operator (`'.timeout_seconds // 86400'`) rather than shell `${:-}` default — the jq approach correctly handles both absent keys and null values in the metadata JSON
- `rsf.toml` program field uses an obvious `/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/...` placeholder (not a relative path or empty string) so users get a clear error if they forget to set it rather than a silent wrong-path failure
- README kept to 118 lines — this is example documentation pointing to Phase 60's full tutorial, not a tutorial itself

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure: `tests/test_dsl/test_infra_config.py::TestInfrastructureConfig::test_custom_provider_with_dict_config` — confirmed present on prior commit (edd4d40) before any Task 2 changes. Not a regression from this plan.

## User Setup Required

None — no external service configuration required. deploy.sh is not executed in this plan.

## Next Phase Readiness

- All integration files complete: workflow.yaml, handlers/, terraform/ (5 files), deploy.sh, rsf.toml, README.md — full registry-modules-demo example ready for end-to-end testing
- User must set absolute path in rsf.toml before running `rsf deploy workflow.yaml`
- Phase 59 can proceed with end-to-end deployment testing using this example

---
*Phase: 57-core-lambda-example*
*Completed: 2026-03-04*
