# Codebase Concerns

**Analysis Date:** 2026-03-11

## Tech Debt

**JSONPath Error Handling — Partial Path Resolution:**
- Issue: JSONPath parser in `src/rsf/io/jsonpath.py` raises `JSONPathError` on missing keys/indices, but has no graceful degradation or null-coalescing options. This mirrors ASL behavior but prevents partial traversal patterns.
- Files: `src/rsf/io/jsonpath.py` (lines 143-163)
- Impact: Workflows that need to handle optional/missing data fields must pre-validate structure or use complex Choice logic as workarounds
- Fix approach: Add optional parameter `strict_mode=True` to `evaluate_jsonpath()` to allow returning `None` for missing paths instead of raising exceptions

**Global Mutable State — Provider Registry:**
- Issue: Provider and intrinsic function registries use module-level dicts with last-write-wins semantics. No validation that providers are registered before use.
- Files: `src/rsf/providers/registry.py` (line 14), `src/rsf/functions/registry.py` (line 8)
- Impact: If module imports occur in unexpected order, providers may be missing at runtime; decorator order matters for intrinsics
- Fix approach: Implement registry initialization checks in factory functions; add startup validation in CLI entry point

**Broad Exception Catching in CLI:**
- Issue: Multiple CLI commands use bare `except Exception as e:` without distinguishing between user errors, system errors, and programming errors.
- Files: `src/rsf/cli/test_cmd.py` (lines 232, 345, 527), `src/rsf/cli/watch_cmd.py` (lines 81, 88, 123), `src/rsf/cli/doctor_cmd.py` (lines 169, 189, 276)
- Impact: Difficult to debug failures; all errors reported with same severity; no distinction between expected vs unexpected failures
- Fix approach: Create custom exception hierarchy (`RSFError`, `ValidationError`, `ProviderError`, etc.); catch and re-wrap specific exceptions with context

**State Machine Executor Complexity:**
- Issue: `_WorldState` executor in `src/rsf/cli/test_cmd.py` (561 lines) handles all 8 state types with complex nested logic and internal exception handling.
- Files: `src/rsf/cli/test_cmd.py` (lines 280-470+)
- Impact: Hard to test individual state behaviors; bug fixes risk side effects; adding new state types requires understanding entire class
- Fix approach: Refactor into strategy pattern with state-type-specific executor classes; extract handler invocation to separate module

---

## Known Bugs

**Test Executor — Choice State Evaluation Incomplete:**
- Symptoms: Choice state evaluation only handles `DataTestRule` directly, not wrapped in `BooleanAndRule`/`BooleanOrRule`/`BooleanNotRule`
- Files: `src/rsf/cli/test_cmd.py` (lines 89-98)
- Trigger: Workflow with nested choice rules like `And: [{condition1}, {condition2}]`
- Workaround: Manually flatten boolean logic into sequential Choice states

**Test Executor — Catch Redirect Missing Handler State:**
- Symptoms: If Catch.Next points to a state that doesn't exist, executor crashes with "State not found"
- Files: `src/rsf/cli/test_cmd.py` (lines 360-375)
- Trigger: Typo in Catch.Next reference during development
- Workaround: Validate workflows with `rsf validate` before running `rsf test`

**WebSocket Message Handler — Missing Type Validation:**
- Symptoms: If client sends JSON without required fields (e.g., `parse` message without `yaml`), error message doesn't help diagnose issue
- Files: `src/rsf/editor/websocket.py` (lines 70-74)
- Trigger: Client bug or malformed editor state
- Workaround: Check browser console and editor logs

---

## Security Considerations

**Temporary File Permissions:**
- Risk: `FileTransport` in `src/rsf/providers/transports.py` writes metadata JSON to temp file with mode 0600, but `tempfile.mkstemp()` creates file with 0600 by default on Unix systems. However, on Windows, permissions are ignored.
- Files: `src/rsf/providers/transports.py` (lines 46-64)
- Current mitigation: Explicit `os.chmod(path, 0o600)` after write; cleanup in finally block
- Recommendations: Document Windows behavior in comments; consider using `NamedTemporaryFile` with context manager for guaranteed cleanup

**CLI Argument Template Injection:**
- Risk: ArgsTransport validates placeholders but does not sanitize `str.format()` output before passing to subprocess
- Files: `src/rsf/providers/transports.py` (lines 135-145)
- Current mitigation: Placeholders restricted to safe field names (no attribute access or indexing); values come from WorkflowMetadata
- Recommendations: Add shell escaping (e.g., `shlex.quote()`) for CLI args before subprocess.run(); document that provider commands should validate metadata

**FastAPI App State — Shared Mutable State:**
- Risk: `app.state.json_schema` and `app.state.inspect_client` stored at app creation time without thread-safety locks
- Files: `src/rsf/editor/server.py` (lines 44), `src/rsf/inspect/server.py` (lines 46-52)
- Current mitigation: Schema is immutable once generated; inspect_client reads only during requests
- Recommendations: If schema generation becomes dynamic in future, add caching with thread-safe dict; document that inspect_client is not thread-safe for mutations

**AWS Credentials in Subprocess Environment:**
- Risk: Provider commands receive full environment including AWS credentials. Custom provider scripts could leak credentials.
- Files: `src/rsf/providers/base.py`, provider implementations
- Current mitigation: Only MetadataTransport and explicit env vars passed to subprocess
- Recommendations: Document that custom provider scripts should not log environment; consider whitelist-based env passing instead of copying entire environment

---

## Performance Bottlenecks

**Code Generation — No Incremental Updates:**
- Problem: `generate()` function always overwrites orchestrator.py and regenerates all handler stubs, even if only one handler changed
- Files: `src/rsf/codegen/generator.py` (lines 42-100)
- Cause: Simple file-write approach; no diff tracking or selective generation
- Improvement path: Add hash-based cache for handler stubs; only write files if content changed; track generated vs user-edited handlers

**Lambda Inspect Client — No Connection Pooling:**
- Problem: Each API call creates new boto3 client via `asyncio.to_thread()`
- Files: `src/rsf/inspect/client.py` (lines 119-120, 139-140)
- Cause: Boto3 client created in `__init__` but blocking calls in to_thread may spawn threads unnecessarily
- Improvement path: Pre-create thread pool executor in client init; reuse for all blocking calls

**JSONPath Tokenization — Regex Compilation Per Call:**
- Problem: `_tokenize()` in `src/rsf/io/jsonpath.py` compiles regex pattern on each field name match
- Files: `src/rsf/io/jsonpath.py` (lines 134)
- Cause: `re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", path[i:])` called for each token
- Improvement path: Pre-compile pattern at module level; use finditer or pre-tokenize path string

**Validation — No Early Exit for Multiple Errors:**
- Problem: `validate_definition()` in `src/rsf/dsl/validator.py` runs all validators even after first error found
- Files: `src/rsf/dsl/validator.py` (lines 45-63)
- Cause: Collects all errors in list instead of returning on first
- Improvement path: Add `fail_fast` parameter; document trade-off between UX (all errors at once) vs performance

---

## Fragile Areas

**Test Executor State Transitions:**
- Files: `src/rsf/cli/test_cmd.py` (lines 211-279)
- Why fragile: Loop-based state machine with manual next_state transitions; no explicit state validation; exception handling at state level may mask bugs
- Safe modification: Add state pre-fetching validation; extract state dispatch to separate function; add comprehensive test coverage for each state type
- Test coverage: State transitions tested via integration tests in `tests/test_examples/` but individual state types lack unit tests

**Validator BFS Traversal:**
- Files: `src/rsf/dsl/validator.py` (lines 420-450)
- Why fragile: Reachability check assumes all states have valid Next/Default references; no cycle detection; Parallel/Map branches not fully validated
- Safe modification: Use explicit visited set to detect cycles; validate that terminal states are actually reachable; add tests for unreachable parallel branches
- Test coverage: `tests/test_dsl/` has validator tests but no cycle or unreachable-state tests

**WebSocket Message Dispatch:**
- Files: `src/rsf/editor/websocket.py` (lines 30-64)
- Why fragile: String-based dispatch without enum; if message type is unknown, no error feedback to client
- Safe modification: Use Enum for message types; add type hints for message payload dicts; test all message types explicitly
- Test coverage: `tests/test_inspect/test_server.py` tests some endpoints but websocket handler not directly tested

**ASL Importer State Conversion:**
- Files: `src/rsf/importer/converter.py` (lines 93-200+)
- Why fragile: Recursively converts nested structures; warning collection is local, may lose context; Distributed Map support is incomplete
- Safe modification: Pre-validate ASL schema before conversion; thread warning context through recursion; document unsupported features clearly
- Test coverage: `tests/test_importer/` has some coverage but edge cases (deeply nested Parallel, ItemReader) untested

---

## Scaling Limits

**Inspect Client Rate Limiter:**
- Current capacity: 12 requests/second with token bucket; capacity = 12 tokens
- Limit: AWS Lambda control-plane API has hard 15 req/s limit per function
- Scaling path: Make rate limiter configurable per region; add adaptive limiting based on observed 429 responses; support multiple concurrent function inspection via shared limiter

**Test Executor Input Data — No Size Limits:**
- Current capacity: Stores all input/output data in `TransitionRecord` if verbose mode enabled
- Limit: Large workflows with many transitions or large payloads exhaust memory
- Scaling path: Add `--max-data-size` CLI option; truncate verbose data to first N bytes; stream results to file instead of memory

**Validation Error Collection — No Pagination:**
- Current capacity: `validate_definition()` collects all errors in list
- Limit: Large workflows with hundreds of referential errors produce very long lists; UX degrades
- Scaling path: Add `max_errors` parameter; include count of suppressed errors; paginate validation output in UI

---

## Dependencies at Risk

**PyYAML — Unsafe Load Exposure:**
- Risk: Project uses `yaml.safe_load()` which is safe, but no explicit rejection of unsafe YAML features
- Impact: Safe by default, but easy to accidentally call `yaml.load()` elsewhere
- Migration plan: Replace all YAML parsing with `ruamel.yaml` for better comments preservation; or add custom loader that rejects tags

**Pydantic v2 — Validation Errors Opaque:**
- Risk: Pydantic `ValidationError.errors()` structure is complex; project flattens it manually in many places
- Impact: Error message formatting inconsistent across CLI commands and WebSocket
- Migration plan: Create `PydanticErrorFormatter` utility; centralize error message generation; update all error handlers to use it

**FastAPI — Global App State Not Thread-Safe:**
- Risk: `app.state` dict assignment is not thread-safe if modified after app creation
- Impact: If schema generation or inspect client initialization needs to be dynamic, races are possible
- Migration plan: Use `fastapi.security` patterns for lazy initialization; or use `contextvars` for request-local state

---

## Missing Critical Features

**No Distributed Map Support:**
- Problem: Importer warns but doesn't convert ItemReader/ItemBatcher/ResultWriter; core DSL has no properties for these
- Blocks: Importing large-scale ASL workflows that use distributed maps; scaling workflows to process 100k+ items
- Priority: Medium (documented as "not supported"); customers can work around with regular Map

**No Durable Execution Recording:**
- Problem: `rsf test` executes locally without recording execution state; no way to inspect past local test runs
- Blocks: Debugging distributed/flaky workflows; forensic analysis; integration with external monitoring
- Priority: Low (local executor is for fast feedback, not production diagnostics)

**No Workflow Composition — No SubWorkflow Invocation Tracking:**
- Problem: SubWorkflow field references child workflows, but no runtime type checking or version pinning
- Blocks: Safe refactoring of child workflows; detecting breaking changes in child workflow signatures
- Priority: Medium (needed for microworkflow architecture)

---

## Test Coverage Gaps

**JSONPath Evaluation — Missing Edge Cases:**
- What's not tested: Attribute access on non-dict objects (context objects); bracket notation with special characters; deeply nested paths
- Files: `src/rsf/io/jsonpath.py`
- Risk: Crash or silent failure on production data structures
- Priority: High

**Choice State Boolean Logic:**
- What's not tested: Nested And/Or/Not combinations; deeply nested rules; empty rule arrays
- Files: `src/rsf/dsl/choice.py`, `src/rsf/cli/test_cmd.py` (executor)
- Risk: Incorrect branch selection in complex decision workflows
- Priority: High

**Provider Transports — FileTransport Cleanup:**
- What's not tested: Cleanup on exception during prepare(); concurrent transports writing to same temp dir
- Files: `src/rsf/providers/transports.py`
- Risk: Orphaned temp files; filename collisions under high concurrency
- Priority: Medium

**Inspect Client — Rate Limiter Under Burst Load:**
- What's not tested: Behavior when 100+ concurrent requests hit rate limiter; token bucket edge cases near rate boundary
- Files: `src/rsf/inspect/client.py` (TokenBucketRateLimiter)
- Risk: Unfair distribution of requests; some requests starve
- Priority: Medium

**Validator — Circular References in SubWorkflows:**
- What's not tested: Child workflow references parent; parent references child (direct cycle); indirect cycles through multiple levels
- Files: `src/rsf/dsl/validator.py`
- Risk: Infinite loops in code generation or validation
- Priority: High

---

## Recommendations by Priority

**Critical (Fix Before Release):**
1. Add cycle detection to validator for SubWorkflow references
2. Improve Choice state evaluation in test executor to handle nested boolean logic
3. Add JSONPath edge case tests for non-dict objects and complex nesting

**High (Fix Within Sprint):**
1. Create custom exception hierarchy for CLI to improve error diagnostics
2. Refactor test executor into state-type-specific handlers
3. Document Windows temp file behavior in FileTransport

**Medium (Future Sprints):**
1. Implement incremental code generation with hash caching
2. Add `fail_fast` parameter to validator
3. Pre-compile regex patterns in JSONPath tokenizer
4. Implement SubWorkflow signature validation and version pinning

*Concerns audit: 2026-03-11*
