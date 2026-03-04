---
phase: 59
slug: tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed, project-wide) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest examples/registry-modules-demo/tests/ -v -m "not integration"` |
| **Full suite command** | `pytest examples/registry-modules-demo/tests/ tests/test_examples/test_registry_modules_demo.py -v` |
| **Estimated runtime** | ~5 seconds (local only), ~300 seconds (with integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest examples/registry-modules-demo/tests/ -v -m "not integration"`
- **After every plan wave:** Run `pytest examples/registry-modules-demo/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds (local tests)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 59-01-01 | 01 | 1 | TEST-01 | unit | `pytest examples/registry-modules-demo/tests/test_local.py -v` | ❌ W0 | ⬜ pending |
| 59-01-02 | 01 | 1 | TEST-01 | unit | `pytest examples/registry-modules-demo/tests/test_handlers.py -v` | ✅ | ⬜ pending |
| 59-02-01 | 02 | 2 | TEST-02 | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "not teardown"` | ❌ W0 | ⬜ pending |
| 59-02-02 | 02 | 2 | TEST-02 | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "log"` | ❌ W0 | ⬜ pending |
| 59-02-03 | 02 | 2 | TEST-03 | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "teardown"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `examples/registry-modules-demo/tests/test_local.py` — stubs for TEST-01 (workflow parsing + handler registration)
- [ ] `tests/test_examples/test_registry_modules_demo.py` — stubs for TEST-02, TEST-03
- [ ] `pyproject.toml` testpaths add `"examples/registry-modules-demo/tests"` — currently missing

*Existing infrastructure covers handler tests (test_handlers.py) and integration harness (conftest.py).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-AWS durable execution SUCCEEDED | TEST-02 | Requires AWS credentials + deployed infrastructure | Run `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration` with AWS_PROFILE=adfs |
| Teardown leaves empty state | TEST-03 | Requires deployed infrastructure to tear down | Included in integration test — runs automatically after happy path |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
