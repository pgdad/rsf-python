---
phase: 56
slug: schema-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | REG-06 | manual-only (code review) | `grep -cE 'version = "[0-9]+\.[0-9]+\.[0-9]+"' examples/registry-modules-demo/terraform/versions.tf` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `examples/registry-modules-demo/terraform/` — directory scaffold
- [ ] `examples/registry-modules-demo/terraform/versions.tf` — Phase 56 deliverable (created during execution)

*Existing pytest infrastructure covers all phases. No new test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| versions.tf contains exact version pins for all 5 modules | REG-06 | File content is documentation, not executable code | Verify no `~>` or `>=` on module version lines; confirm 5 exact version strings present |
| durable_config variable names match v8.7.0 source | REG-06 | Verification against external GitHub source | Confirm `durable_config_execution_timeout` and `durable_config_retention_period` documented |
| Lambda alias convention documented with #45800 rationale | REG-06 | Design decision documentation | Confirm alias convention and issue reference present in findings |
| IAM approach decision with verification evidence | REG-06 | Design decision documentation | Confirm managed + inline hybrid approach documented with action name mapping |
| Zip path convention established | REG-06 | Design decision documentation | Confirm `build/function.zip` path and `${path.module}/../build/function.zip` reference documented |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
