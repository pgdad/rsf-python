---
phase: 60
slug: tutorial-document
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 60 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — documentation phase (Markdown file) |
| **Config file** | none |
| **Quick run command** | `test -f tutorials/09-custom-provider-registry-modules.md` |
| **Full suite command** | `grep -c "^## Step" tutorials/09-custom-provider-registry-modules.md` + manual review |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `test -f tutorials/09-custom-provider-registry-modules.md`
- **After every plan wave:** Run full grep checks below
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 0 | TUT-01 | smoke | `test -f tutorials/09-custom-provider-registry-modules.md && grep -c "^## Step" tutorials/09-custom-provider-registry-modules.md` | ❌ W0 | ⬜ pending |
| 60-01-02 | 01 | 0 | TUT-02 | smoke | `grep -c "RSF TerraformProvider output" tutorials/09-custom-provider-registry-modules.md` (expect >= 2) | ❌ W0 | ⬜ pending |
| 60-01-03 | 01 | 0 | TUT-03 | smoke | `grep -c "workflow_name\|dynamodb_tables\|dlq_enabled" tutorials/09-custom-provider-registry-modules.md` (expect >= 3) | ❌ W0 | ⬜ pending |
| 60-01-04 | 01 | 0 | TUT-04 | smoke | `grep -c "absolute path\|chmod\|create_package\|version pin\|durable IAM" tutorials/09-custom-provider-registry-modules.md` (expect >= 4) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tutorials/09-custom-provider-registry-modules.md` — the tutorial file itself (Phase 60 deliverable)

*No test framework gaps — documentation phases verified by smoke grep commands against the output file.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tutorial readability and flow | TUT-01 | Prose quality requires human review | Read through all steps in order |
| HCL comparison accuracy | TUT-02 | Content correctness vs source templates | Compare tutorial HCL blocks against main.tf.j2 and dynamodb.tf.j2 |
| Schema table completeness | TUT-03 | All fields present with correct types | Cross-check against WorkflowMetadata dataclass |
| Pitfall symptom accuracy | TUT-04 | Error messages must match real behavior | Verify error messages against actual failure modes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
