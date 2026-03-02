---
phase: 41-alerts-dead-letter-queues-and-multi-stage-deploy
plan: 03
subsystem: cli, infra
tags: [multi-stage, deploy, terraform, tfvars, cli]

requires:
  - phase: 41-alerts-dead-letter-queues-and-multi-stage-deploy
    provides: DLQ support (plan 02)
provides:
  - --stage CLI option on rsf deploy command
  - Stage-specific Terraform directory isolation (terraform/<stage>/)
  - Stage variable file resolution (stages/<stage>.tfvars)
  - -var-file passing to terraform apply for stage overrides
  - Stage variable in variables.tf.j2
affects: [phase-42, phase-44]

tech-stack:
  added: []
  patterns: [stage-isolated-terraform-dirs, tfvars-override-pattern]

key-files:
  created: []
  modified:
    - src/rsf/cli/deploy_cmd.py
    - src/rsf/terraform/generator.py
    - src/rsf/terraform/templates/variables.tf.j2
    - tests/test_cli/test_deploy.py
    - tests/test_terraform/test_terraform.py

key-decisions:
  - "Stage isolation via separate Terraform directories (terraform/prod/, terraform/dev/) — each gets its own state"
  - "Stage variable files follow convention: stages/<stage>.tfvars in workflow directory"
  - "-var-file passed to terraform apply (not init, which doesn't support it)"
  - "Stage var file is required when --stage is provided — clear error with example content if missing"

patterns-established:
  - "Multi-stage pattern: tf_dir/<stage> isolation + stages/<stage>.tfvars override + -var-file terraform argument"

requirements-completed: [DSL-07]

duration: 5min
completed: 2026-03-01
---

# Plan 41-03: Multi-Stage Deployment Summary

**Multi-stage deployment support via --stage CLI option with stage-isolated Terraform directories and stage-specific variable overrides**

## Performance

- **Duration:** 5 min
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- --stage CLI option on rsf deploy command (e.g., rsf deploy --stage prod)
- Stage-specific Terraform directory isolation (terraform/prod/, terraform/dev/)
- Stage variable file resolution from stages/<stage>.tfvars with helpful error on missing file
- -var-file passed to terraform apply and targeted code-only apply
- Stage variable conditionally added to variables.tf.j2 template
- stage field added to TerraformConfig dataclass
- 11 new tests (8 deploy CLI + 3 Terraform), 471 unit tests passing with zero regressions

## Task Commits

1. **Task 1: Add --stage CLI option and stage variable file resolution** - `69e6546` (feat)

## Files Created/Modified
- `src/rsf/cli/deploy_cmd.py` - Added --stage option, stage tf_dir isolation, stage var file resolution, -var-file passing to terraform apply
- `src/rsf/terraform/generator.py` - Added stage field to TerraformConfig, passed to template context
- `src/rsf/terraform/templates/variables.tf.j2` - Conditional stage variable block
- `tests/test_cli/test_deploy.py` - TestStageDeployment class with 8 tests
- `tests/test_terraform/test_terraform.py` - TestStageConfig class with 3 tests

## Decisions Made
- Stage isolation through separate Terraform directories (terraform/<stage>/) for independent state
- Stage variable files at stages/<stage>.tfvars (workflow directory convention)
- terraform init does NOT receive -var-file (unsupported), only terraform apply does
- --stage with --no-infra is allowed (stage is ignored since no Terraform is generated)

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - users create stages/<stage>.tfvars files as needed.

## Next Phase Readiness
- Multi-stage deployment complete
- Phase 41 fully complete (alarms, DLQ, multi-stage)

---
*Plan: 41-03*
*Completed: 2026-03-01*
