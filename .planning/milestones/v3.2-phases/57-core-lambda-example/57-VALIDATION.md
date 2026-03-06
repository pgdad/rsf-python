---
phase: 57
slug: core-lambda-example
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (confirmed from pyproject.toml) |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Example-local run** | `pytest examples/registry-modules-demo/tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v && pytest examples/registry-modules-demo/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + manual `rsf deploy` on example
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 57-01-01 | 01 | 1 | PROV-01 | unit | `pytest tests/test_providers/test_transports.py -x -q` | ✅ | ⬜ pending |
| 57-01-02 | 01 | 1 | PROV-02 | unit | `pytest tests/test_config.py -x -q` | ✅ | ⬜ pending |
| 57-01-03 | 01 | 1 | PROV-03 | unit | `pytest tests/test_cli/test_deploy.py -x -q -k teardown` | ❌ W0 | ⬜ pending |
| 57-01-04 | 01 | 1 | PROV-04 | manual | `bash examples/registry-modules-demo/deploy.sh deploy` | ❌ W0 | ⬜ pending |
| 57-02-01 | 02 | 1 | REG-01 | manual | `cd examples/registry-modules-demo/terraform && terraform plan` | ❌ W0 | ⬜ pending |
| 57-02-02 | 02 | 1 | EXAM-01 | unit | `pytest -x -q -k "registry" tests/test_dsl/` | ❌ W0 | ⬜ pending |
| 57-02-03 | 02 | 1 | EXAM-02 | manual | `ls examples/registry-modules-demo/` | ❌ W0 | ⬜ pending |
| 57-02-04 | 02 | 1 | EXAM-03 | unit | `pytest examples/registry-modules-demo/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 57-03-01 | 03 | 1 | TOOL-01 | unit | `pytest tests/test_cli/test_deploy.py -x -q -k teardown` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/rsf/cli/deploy_cmd.py` — add `--teardown` flag and `_teardown_infra()` function (TOOL-01)
- [ ] `tests/test_cli/test_deploy.py` — add teardown test cases
- [ ] `examples/registry-modules-demo/workflow.yaml` — new example workflow
- [ ] `examples/registry-modules-demo/handlers/` — handler files with `@state` decorators
- [ ] `examples/registry-modules-demo/tests/conftest.py` and `test_handlers.py`
- [ ] `examples/registry-modules-demo/terraform/main.tf` — after managed policy check
- [ ] `examples/registry-modules-demo/terraform/variables.tf`
- [ ] `examples/registry-modules-demo/terraform/outputs.tf`
- [ ] `examples/registry-modules-demo/deploy.sh` (chmod +x)
- [ ] `examples/registry-modules-demo/rsf.toml`
- [ ] `examples/registry-modules-demo/README.md`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lambda Durable Function deploys to AWS | REG-01 | Requires live AWS account | `rsf deploy` on registry-modules-demo, verify Lambda in AWS console |
| deploy.sh zips and runs terraform apply | PROV-04 | Requires Terraform and AWS | Run `deploy.sh deploy`, check build/function.zip exists and Lambda is live |
| Teardown destroys all resources | PROV-03 | Requires live AWS state | `rsf deploy --teardown`, verify no Lambda/IAM resources remain |
| Managed policy availability check | REG-01 | Requires AWS credentials | `aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
