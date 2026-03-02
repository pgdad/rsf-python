# Pitfalls Research

**Domain:** Pluggable infrastructure providers for existing Terraform-coupled CLI tool (RSF v3.0)
**Researched:** 2026-03-02
**Confidence:** HIGH (based on direct codebase analysis + verified against Python docs and IaC ecosystem sources)

---

## Critical Pitfalls

### Pitfall 1: The Leaky Abstraction — Provider Interface Encodes Terraform Assumptions

**What goes wrong:**
The new `InfrastructureProvider` interface is defined around Terraform's mental model — files like `tf_dir`, `backend_key`, `TerraformConfig` dataclass fields — with thin renaming. CDK and custom providers then have to accept parameters they don't use (e.g., `backend_bucket`, `backend_key`, `tf_dir`), or developers add CDK-specific fields directly to the shared interface. The abstraction breaks within one sprint.

**Why it happens:**
The existing `deploy_cmd.py` builds a `TerraformConfig` dataclass with 15 Terraform-specific fields before calling `generate_terraform()`. Developers extracting the interface often copy this shape wholesale. It feels fast — the abstraction "exists" — but it encodes one provider's needs as universal.

**How to avoid:**
The provider interface must speak *workflow semantics*, not IaC tool semantics. It passes `WorkflowMetadata` (name, states, triggers, DynamoDB tables, alarms, DLQ, lambda_url — all from the DSL model) plus a `ProviderConfig` (opaque key-value pairs the provider interprets). Each provider translates that into its own tool's config internally. The `TerraformConfig` dataclass stays internal to the Terraform provider.

**Warning signs:**
- Interface method signatures contain the words `terraform`, `tf_dir`, `hcl`, `backend`
- CDK provider implementation has attributes it ignores or sets to `None`
- Interface has more than ~5 parameters in `provision()` / `destroy()` signatures
- The word `TerraformConfig` appears in any file outside `src/rsf/terraform/`

**Phase to address:**
Provider interface definition phase (first provider-system phase). The interface contract must be finalized before any provider is implemented. Write a CDK provider stub in the same phase to validate the interface is genuinely tool-agnostic.

---

### Pitfall 2: Breaking Existing Terraform Users by Changing the Default Behavior

**What goes wrong:**
The `rsf deploy` command currently runs `terraform init` then `terraform apply` with `--tf-dir terraform` as the default. After refactoring, it routes through a provider dispatch layer. If the dispatch logic defaults to the wrong provider, or if it requires explicit `--provider terraform` to get the old behavior, every existing user's workflow breaks silently — their `rsf deploy` either fails with an obscure error or deploys nothing.

**Why it happens:**
Provider selection requires configuration. Developers add a `provider:` key to `workflow.yaml` or a project config file. The "default when nothing is configured" case is forgotten or set to `None`, causing `AttributeError` or silent no-op on the first run after upgrade.

**How to avoid:**
- Default provider is always `terraform` — no config required to preserve existing behavior
- Provider detection order: `workflow.yaml` `infrastructure.provider` → project config → hard default `"terraform"`
- Existing Terraform users must get identical behavior with zero config changes
- Write a regression test that runs `rsf deploy` against a v2.0-style `workflow.yaml` (no `infrastructure:` section) and asserts Terraform is invoked

**Warning signs:**
- `rsf deploy` requires `--provider` flag where it previously did not
- CLI help text changed from "deploys via Terraform" to vague "deploys via configured provider"
- Test suite has no test for the "no infrastructure config" code path
- `workflow.yaml` schema marks `infrastructure.provider` as required rather than optional with default

**Phase to address:**
Provider dispatch / default selection phase. A dedicated backward-compatibility test must be a success criterion, not an afterthought.

---

### Pitfall 3: Subprocess Deadlock on Long-Running `terraform apply` / `cdk deploy`

**What goes wrong:**
The existing `deploy_cmd.py` uses `subprocess.run(["terraform", "apply"], cwd=tf_dir, check=True)` — this works for Terraform because `terraform apply` streams to the terminal directly (no PIPE). When implementing a generic provider that captures output for error reporting, developers switch to `capture_output=True` or `stdout=PIPE, stderr=PIPE`. A long CDK deploy generates substantial output; the pipe buffer fills (typically 64 KB on Linux); the child process blocks writing; the parent blocks waiting for the process to exit — deadlock. The CLI hangs indefinitely.

**Why it happens:**
`subprocess.run(..., capture_output=True)` is convenient for short commands. It is documented as "equivalent to Popen followed by communicate()" but this only prevents deadlock if `communicate()` is used — which `subprocess.run` does do internally. The real trap is `Popen` with manual `stdout.read()` or `stderr.read()` calls in sequence rather than concurrent reads.

Secondary trap: developers use `Popen` to stream real-time output with `stdout.readline()`, forgetting to drain stderr concurrently. When stderr fills, the subprocess blocks.

**How to avoid:**
- For passthrough (interactive) invocation: `subprocess.run(cmd, cwd=..., check=True)` with no PIPE — output goes straight to terminal. This is what Terraform and CDK both expect for user-facing deploys.
- For captured invocation (testing, error extraction): `subprocess.run(cmd, capture_output=True, text=True, timeout=N)` — safe because `run` uses `communicate()` internally.
- For real-time streaming with capture: use `Popen` with `stdout=PIPE, stderr=PIPE` and read both streams concurrently with threads — never read stdout and stderr sequentially.
- Set explicit timeouts on all subprocess calls. Terraform apply and CDK deploy can run 10-30 minutes; timeouts should be configurable per-provider, not hardcoded.

**Warning signs:**
- Code uses `proc = Popen(...)` then `proc.stdout.read()` then `proc.stderr.read()` in sequence
- No timeout parameter on any `subprocess.run()` or `Popen()` call
- Provider test suite hangs rather than fails on malformed provider config
- `capture_output=True` and `stderr=subprocess.STDOUT` used together (raises `ValueError` — mutually exclusive)

**Phase to address:**
Provider base class / subprocess utility phase. Build a shared `run_provider_command()` helper that handles passthrough vs. capture modes correctly. All providers use this helper; no provider calls `subprocess` directly.

---

### Pitfall 4: Swallowing Provider Error Messages — Silent Failure

**What goes wrong:**
The provider invokes an external tool (`terraform apply`, `cdk deploy`, a custom script). The tool fails with a detailed error message on stderr. The provider catches `subprocess.CalledProcessError`, prints "Provider failed (exit 1)", and exits. The user sees no actionable information — they have to hunt for logs or re-run manually.

The existing `deploy_cmd.py` already has this pattern:
```python
except subprocess.CalledProcessError as exc:
    console.print(f"[red]Error:[/red] terraform apply failed (exit {exc.returncode})")
    raise typer.Exit(code=1)
```
`exc.stderr` and `exc.stdout` are `None` here because `capture_output` was not set — all output already went to terminal, so the user did see it. Once a generic provider abstracts this and adds `capture_output=True` for uniformity, the output disappears.

**Why it happens:**
The abstraction hides the subprocess call, so the error context (stderr content) must be explicitly threaded back through the provider interface. Developers forget to forward it, or they print a generic message for all providers.

**How to avoid:**
- Passthrough mode (no capture): subprocess output goes to terminal during execution. On failure, `CalledProcessError` is raised; the user already saw the error on screen.
- Captured mode: on `CalledProcessError`, re-print `exc.stderr` (or `exc.stdout` if the tool writes errors there) before raising. Never swallow stderr.
- Provider interface should have a `verbose: bool` flag — in non-verbose mode, capture and only show on failure; in verbose mode, passthrough to terminal.
- CDK is known to write errors to both stdout and stderr inconsistently — capture both, show both on failure.

**Warning signs:**
- `subprocess.CalledProcessError` caught and `exc.stderr` not accessed or printed
- Error message says "provider failed" without including the tool's own error text
- Test for provider failure only checks exit code, not that error text was surfaced

**Phase to address:**
Provider base class / subprocess utility phase. The `run_provider_command()` helper must handle error forwarding as part of its contract, not left to individual providers.

---

### Pitfall 5: Metadata Format Mismatch — CDK Provider Gets Wrong Shape

**What goes wrong:**
The Terraform provider uses `TerraformConfig` — a rich, structured Python dataclass. The CDK provider and custom providers receive workflow metadata via: (a) a JSON file, (b) environment variables, or (c) CLI args. Each provider interprets slightly different field names for the same concept. A DynamoDB table defined as `partition_key.name` in `TerraformConfig` arrives as `PARTITION_KEY_NAME` in env vars, but the CDK template expects `partitionKeyName` in JSON. Bugs appear only when DynamoDB is configured — rare edge case that escapes initial testing.

**Why it happens:**
The metadata serialization format is defined per-provider rather than in the core. Each provider author makes independent naming choices. No canonical schema exists.

**How to avoid:**
- Define a single `WorkflowMetadata` JSON schema (separate from `TerraformConfig`) that all providers receive
- The JSON shape mirrors the DSL YAML structure (snake_case, matching field names) — not Terraform's or CDK's conventions
- Providers receive the JSON file path as a single argument; they parse it themselves
- Validate the JSON against the schema before passing it to any provider — fail fast if RSF's metadata serialization has a bug
- Write a metadata serialization test for every DSL feature (triggers, DynamoDB, alarms, DLQ, lambda_url) before writing any provider

**Warning signs:**
- Different providers receive metadata via different mechanisms (some via env vars, some via JSON, some via CLI args) with no shared contract
- `TerraformConfig` fields are mapped to env vars one-to-one (perpetuating Terraform's naming)
- No JSON schema file for the metadata format
- Metadata tests only cover the happy path (simple workflow, no triggers, no DynamoDB)

**Phase to address:**
Metadata specification phase, before any provider implementation. Define the schema first, implement serialization, write schema tests, then implement providers against the schema.

---

### Pitfall 6: Provider Configuration Validated Too Late — Error at Runtime, Not Load Time

**What goes wrong:**
A user configures `infrastructure.provider: cdk` in their `workflow.yaml` but omits required CDK fields (e.g., CDK app entry point, stack name). RSF loads the workflow, validates DSL structure, generates code — then calls the CDK provider, which discovers missing config and raises a `KeyError` mid-deploy, after Terraform state may or may not exist, leaving the user uncertain about what was provisioned.

**Why it happens:**
Pydantic validates the DSL model fields — it knows nothing about provider-specific config. Provider config is an opaque `dict` or freeform YAML block. Validation is deferred to provider instantiation or even to the subprocess invocation.

**How to avoid:**
- Each provider implements a `validate_config(config: dict) -> list[str]` method that returns error strings
- `rsf validate` calls all provider config validators, not just DSL validators
- `rsf doctor` checks that the configured provider's binary exists (e.g., `cdk` in PATH for CDK provider)
- Provider config schema is documented as a Pydantic model inside each provider module — even if the DSL stores it as a raw dict, the provider validates it against this model on load
- Fail at `rsf validate` time, not at `rsf deploy` time

**Warning signs:**
- Provider `__init__` accesses `config["key"]` without try/except or `.get()`
- `rsf validate` success does not guarantee `rsf deploy` will have valid provider config
- `rsf doctor` output still shows only "Terraform" as the binary check after v3.0 ships
- No test for "deploy fails gracefully when CDK config is missing required field"

**Phase to address:**
Provider interface definition phase. `validate_config()` must be part of the interface contract from day one, not retrofitted.

---

### Pitfall 7: The `diff_cmd.py` and `doctor_cmd.py` Remain Terraform-Coupled After Provider Abstraction

**What goes wrong:**
The provider abstraction in `deploy_cmd.py` is complete. But `diff_cmd.py` still looks for `terraform/terraform.tfstate`, and `doctor_cmd.py` hardcodes a Terraform binary check as a FAIL (not WARN) for all users. A CDK user runs `rsf diff` and gets "No deployed state found" because the diff command only knows how to read Terraform state. `rsf doctor` reports FAIL because `terraform` is not installed, even though the user is using CDK.

**Why it happens:**
Commands are implemented in isolation. The provider abstraction is applied to `deploy_cmd.py` first, then developers run out of scope or time. The other commands that have Terraform-specific paths are not on the refactoring checklist.

**How to avoid:**
- Audit all 16 commands for Terraform-specific paths before writing any code
- Known affected commands: `deploy`, `diff`, `doctor`, `watch` (uses Terraform-targeted apply), `cost` (reads Terraform outputs), `export` (may reference Terraform state)
- Each command must either: (a) go through the provider abstraction, or (b) explicitly document that it is Terraform-only and degrade gracefully for other providers
- `rsf doctor` Terraform check must become WARN (not FAIL) when provider is CDK or custom

**Warning signs:**
- Any command imports from `rsf.terraform.*` after the abstraction phase
- `diff_cmd.py` still references `terraform.tfstate` by name
- `doctor_cmd.py` `ENV_CHECK_NAMES` still includes `"Terraform"` as a hard FAIL check
- `watch_cmd.py` `run_cycle()` still calls `terraform apply -target=aws_lambda_function.*` directly

**Phase to address:**
A dedicated "provider-aware command audit" phase. This is not a cosmetic change — each affected command requires design decisions about what it means for non-Terraform providers.

---

### Pitfall 8: External Program Path Injection via User-Supplied Provider Config

**What goes wrong:**
The custom provider feature allows users to specify an arbitrary program path in config: `infrastructure.provider: custom` with `program: /path/to/my-deploy.sh`. If RSF passes workflow metadata as environment variables and the program path or metadata values contain shell metacharacters, a user with a malicious or misconfigured workflow.yaml could cause unintended command execution or environment variable injection.

**Why it happens:**
`subprocess.run(cmd, shell=True)` with string interpolation of user-supplied values is the fast path — it works for simple cases. Developers who test with benign values miss the injection vector.

**How to avoid:**
- Always use `shell=False` (the default) — pass arguments as a list, never as a string
- Validate the `program` path exists before invocation; reject paths that are not absolute or not executable
- Pass metadata via JSON file, not environment variable injection — env var values from user config are not sanitized by the subprocess module
- If env vars must be used, construct the env dict explicitly; never merge user-supplied dicts into `os.environ` directly
- Log the exact command being invoked (minus sensitive values) so users can debug custom providers

**Warning signs:**
- Code uses `subprocess.run(f"{config['program']} {args}", shell=True)`
- `os.environ.update(user_supplied_dict)` before subprocess call
- No validation that `program` path exists before invocation
- Program path accepted as relative path (depends on `cwd`, not explicit)

**Phase to address:**
Custom provider implementation phase. Security review of the subprocess invocation must be a success criterion before shipping custom provider support.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `TerraformConfig` as the shared metadata type | No new dataclass to define | CDK/custom providers leak Terraform field names into their config; interface cannot evolve without breaking Terraform provider | Never |
| Validate provider config only in `deploy_cmd` | Simpler code path | Errors surface at deploy time after code generation; no `rsf validate` integration | Never |
| Use `shell=True` for custom provider invocation | Easier argument construction | Security vulnerability; PATH-dependent behavior; untestable on Windows | Never |
| Leave `doctor_cmd.py` Terraform-hardcoded | No change to working code | CDK users see false FAIL; erodes trust in doctor command | Only temporarily — fix within same milestone |
| Skip real-time streaming; always use `capture_output=True` | Simpler subprocess handling | Terraform/CDK deploy output appears only after completion (can be 10+ minutes); UX regression for existing users | Never for long-running commands |
| Add provider config to DSL Pydantic model directly | Single validation pass | DSL model becomes provider-aware; adding a new provider requires changing core DSL models | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Terraform subprocess | `capture_output=True` hides interactive prompts; user cannot answer `yes` to apply | Use passthrough (no PIPE) for interactive commands; only capture for `--auto-approve` equivalent |
| CDK subprocess | CDK CLI (`cdk deploy`) writes errors to stdout, not stderr, inconsistently | Capture both streams; show both on failure |
| CDK bootstrap | `cdk deploy` fails with cryptic "Subprocess exited with error null" if bootstrap not run | CDK provider must check/run `cdk bootstrap` before first deploy; add to `rsf doctor` |
| Custom provider | Program exits 0 but operation failed (soft failure) | Provider interface must define what exit code 0 means; custom provider docs must specify expected exit codes |
| Metadata JSON | JSON written to temp file with predictable path is world-readable | Write to `tempfile.NamedTemporaryFile` with mode 0600; delete after provider exits |
| `rsf watch --deploy` | Watch loop calls provider on every file change; CDK deploy takes minutes | Watch's `--deploy` flag must respect provider timeout; add debounce or disable `--deploy` for slow providers |
| Stage isolation | Terraform uses `terraform/prod/` directory; CDK uses CDK context/environment | Stage concept must be passed as metadata, not as directory path convention — CDK doesn't use the directory |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Provider instantiation on every CLI invocation | Slow `rsf validate` because provider is loaded and validated even when not deploying | Load provider lazily (only in `deploy_cmd`, not `validate_cmd`) | Immediately visible; degrades DX |
| CDK synth on every `rsf diff` | `rsf diff` takes 2+ minutes because CDK synth is expensive | `diff` command must not invoke the provider's synth/plan step unless `--provider-plan` flag is given | Every `rsf diff` invocation |
| Subprocess search in PATH on every call | `shutil.which("terraform")` called N times per command | Cache binary resolution at provider init time | Negligible at current scale |
| JSON metadata file not cleaned up | Temp files accumulate in `/tmp` containing workflow metadata | Use context manager or `try/finally` to ensure deletion | After 1000+ deploys on long-running workstation |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `shell=True` with user-supplied program path | Command injection via metacharacters in path or workflow name | Always `shell=False`; args as list |
| Metadata JSON in predictable temp path | Another process reads workflow metadata (DynamoDB table names, ARNs) | `tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)` with explicit `os.chmod(path, 0o600)` |
| Passing AWS credentials as metadata | Credentials in JSON file or env vars passed to untrusted custom providers | Never include credentials in metadata; providers inherit AWS credentials from the environment through standard SDK mechanisms |
| Workflow name in subprocess args without sanitization | Workflow names with spaces or shell chars cause argument splitting | Always pass as list element, not string interpolation; `workflow_name` already has `sanitize_name()` — use it |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress output during long CDK deploy | User sees nothing for 10+ minutes; unclear if hung or working | Passthrough subprocess output to terminal; add elapsed time indicator |
| `rsf doctor` fails for Terraform when user chose CDK | User thinks something is broken; "FAIL: terraform not found" | Make Terraform check provider-aware: PASS/WARN/FAIL depends on configured provider |
| `rsf deploy --provider cdk` but CDK not installed | Error surfaces after code generation | `rsf doctor` and deploy pre-flight check for provider binary before code generation |
| Provider config in two places (workflow.yaml and project config) | User confused about which takes precedence | Clear documented precedence: workflow.yaml > project config > default; show resolved provider in `rsf deploy` output |
| Custom provider stderr swallowed | User's script fails; RSF says "Provider failed (exit 1)"; no details | Always forward provider stderr to console on failure |

---

## "Looks Done But Isn't" Checklist

- [ ] **Provider abstraction:** `deploy_cmd.py` refactored, but `watch_cmd.py` still has `terraform apply -target=aws_lambda_function.*` hardcoded — verify `watch --deploy` goes through provider
- [ ] **Backward compatibility:** `rsf deploy` with a v2.0 `workflow.yaml` (no `infrastructure:` block) tested and confirmed to invoke Terraform — do not rely on manual testing only
- [ ] **Metadata completeness:** Metadata serialization covers all DSL features — triggers (all 3 types), DynamoDB tables, alarms, DLQ, lambda_url — not just the simple case
- [ ] **CDK bootstrap check:** CDK provider checks if bootstrap is needed before first deploy; `rsf doctor` reports CDK bootstrap status
- [ ] **Provider validation in `rsf validate`:** `rsf validate workflow.yaml` calls provider's `validate_config()` and reports errors — not just DSL validation
- [ ] **`rsf doctor` provider-aware:** Terraform binary check is WARN (not FAIL) when provider is CDK or custom
- [ ] **`rsf diff` provider-aware:** Diff command does not crash when `terraform/terraform.tfstate` does not exist because user is on CDK
- [ ] **Error forwarding:** CDK/custom provider failure shows the tool's own error message, not just exit code
- [ ] **Security review:** Custom provider invocation uses `shell=False`; metadata temp file has restricted permissions
- [ ] **Subprocess timeout:** All provider subprocess calls have an explicit, configurable timeout — not infinite

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Leaky interface (Terraform-shaped) | HIGH | Re-design interface; update both providers; update all callers; re-test all providers |
| Breaking default provider selection | MEDIUM | Add default detection logic; write regression test; patch release |
| Subprocess deadlock in production | HIGH | Requires user to kill CLI process; add timeout as hotfix; no automated recovery |
| Silent failure (error swallowed) | LOW | Add `exc.stderr` forwarding; patch release |
| Metadata format mismatch | MEDIUM | Define canonical schema retroactively; update provider; update serializer |
| Provider config validated too late | LOW | Move validation to `validate_cmd`; minor refactor |
| Injection vulnerability in custom provider | CRITICAL | Remove `shell=True`; patch release immediately; security advisory if shipped |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Leaky abstraction (Terraform-shaped interface) | Provider interface definition | CDK stub implements interface with zero Terraform-specific fields |
| Breaking default Terraform behavior | Provider dispatch / default selection | Regression test: v2.0 workflow.yaml deploys via Terraform with no config |
| Subprocess deadlock | Provider base class / subprocess helper | Stress test with provider that generates large stdout output |
| Silent error swallowing | Provider base class / subprocess helper | Test: provider exits 1 → CLI shows provider's stderr content |
| Metadata format mismatch | Metadata specification (before providers) | JSON schema test: all DSL features serialize to canonical schema |
| Provider config validated too late | Provider interface definition | `rsf validate` with invalid CDK config returns error before deploy |
| Terraform-coupled non-deploy commands | Provider-aware command audit phase | `rsf doctor` with `provider: cdk` → Terraform check is WARN not FAIL |
| Injection via custom provider path | Custom provider implementation | Security test: workflow name with shell chars; `shell=False` assertion |

---

## Sources

- Direct codebase analysis: `/home/esa/git/rsf-python/src/rsf/cli/deploy_cmd.py`, `doctor_cmd.py`, `watch_cmd.py`, `diff_cmd.py`
- Direct codebase analysis: `/home/esa/git/rsf-python/src/rsf/terraform/generator.py`, `engine.py`
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) — deadlock risks, `capture_output` behavior, `communicate()` contract
- [Python bug tracker: capture_output + stderr=STDOUT conflict](https://bugs.python.org/issue36760) — `ValueError` on conflicting capture params
- [AWS CDK GitHub: "Subprocess exited with error null"](https://github.com/aws/aws-cdk/issues/28637) — CDK exit code opacity
- [CDK GitHub: cdk deploy exit code 137 from Node.js child process](https://github.com/hashicorp/terraform-cdk/issues/3499) — exit code unreliability
- [Terraform GitHub: terraform apply returning 0 on error](https://github.com/hashicorp/terraform/issues/20671) — exit code trust issues
- [Branch by Abstraction pattern (AWS Prescriptive Guidance)](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/branch-by-abstraction.html) — migration without breakage
- [Sourcery: Python subprocess tainted env args vulnerability](https://www.sourcery.ai/vulnerabilities/python-lang-security-audit-dangerous-subprocess-use-tainted-env-args) — injection via env
- [Python abc module documentation](https://docs.python.org/3/library/abc.html) — ABC vs Protocol for provider interface
- [PEP 544 Protocols](https://peps.python.org/pep-0544/) — structural subtyping; `isinstance` behavior with `@runtime_checkable`
- [Real-time subprocess output — Eli Bendersky](https://eli.thegreenplace.net/2017/interacting-with-a-long-running-child-process-in-python/) — correct Popen streaming patterns
- [CDKTF sunset notice (December 2025)](https://github.com/hashicorp/terraform-cdk) — CDK for Terraform deprecated; native AWS CDK (`aws-cdk-lib`) is the correct CDK target

---
*Pitfalls research for: RSF v3.0 — Pluggable Infrastructure Providers*
*Researched: 2026-03-02*
