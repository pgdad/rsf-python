---
phase: "54"
status: passed
verified: "2026-03-02"
---

# Phase 54: Custom Provider - Verification

## Phase Goal
Users can configure any external program as an infrastructure provider; metadata reaches the program via the user's chosen transport; subprocess invocation is security-hardened.

## Success Criteria Verification

### SC1: Custom provider configuration in workflow YAML
**Status:** PASSED

User can configure `infrastructure: provider: custom` with `program: /path/to/my-script.sh` and `args: [deploy, --env, {stage}]` in workflow YAML. The `CustomProviderConfig` Pydantic model validates the configuration with typed fields. `InfrastructureConfig.custom` is typed as `CustomProviderConfig | None`.

**Evidence:**
- `CustomProviderConfig` in `src/rsf/dsl/models.py` with program, args, teardown_args, metadata_transport, env, timeout fields
- `InfrastructureConfig.custom: CustomProviderConfig | None` replaces the `dict[str, Any]` placeholder
- `register_provider("custom", CustomProvider)` in `src/rsf/providers/__init__.py`
- `get_provider("custom")` returns a `CustomProvider` instance
- 16 config tests pass, 11 integration tests pass

### SC2: Security-hardened subprocess invocation
**Status:** PASSED

The custom provider subprocess call always uses `shell=False`. The program path is validated as an absolute path and executable before invocation. No string interpolation into shell commands occurs.

**Evidence:**
- `CustomProvider.run_provider_command_streaming()` always uses `shell=False`
- `CustomProvider._validate_program()` checks `Path.is_absolute()`, `Path.exists()`, and `os.access(path, os.X_OK)`
- No f-string or `.format()` used to build command strings -- commands built as `list[str]`
- 34 provider tests verify security properties
- Tests confirm ValueError for relative paths, FileNotFoundError for missing programs, PermissionError for non-executable

### SC3: Metadata transport selection
**Status:** PASSED

User can select which metadata transport (JSON file, env vars, or CLI args) the custom provider receives via a `metadata_transport:` field in the `custom:` block. All three transports work independently.

**Evidence:**
- `metadata_transport: Literal["file", "env", "args"]` field in `CustomProviderConfig`
- `CustomProvider._create_transport()` maps "file" -> FileTransport, "env" -> EnvTransport, "args" -> ArgsTransport
- Integration tests verify each transport:
  - File transport: `RSF_METADATA_FILE` env var set
  - Env transport: `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON` env vars set
  - Args transport: `{workflow_name}`, `{stage}` placeholders substituted in command
- Transport cleanup verified in try/finally block (both success and error paths)

## Requirement Coverage

| ID | Description | Plans | Status |
|----|-------------|-------|--------|
| CUST-01 | Configure arbitrary program as infrastructure provider | 01, 02, 03 | VERIFIED |
| CUST-02 | shell=False with security-hardened subprocess | 02, 03 | VERIFIED |
| CUST-03 | Select metadata transport (file/env/args) | 02, 03 | VERIFIED |

## Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| test_custom_config.py | 16 | PASSED |
| test_custom_provider.py | 34 | PASSED |
| test_custom_integration.py | 11 | PASSED |
| **Total new** | **61** | **PASSED** |
| **Total provider suite** | **169** | **PASSED** |

## Files Created/Modified

### New Files
- `src/rsf/providers/custom.py` -- CustomProvider class (281 lines)
- `tests/test_providers/test_custom_config.py` -- Config model tests (16 tests)
- `tests/test_providers/test_custom_provider.py` -- Provider tests (34 tests)
- `tests/test_providers/test_custom_integration.py` -- Integration tests (11 tests)

### Modified Files
- `src/rsf/dsl/models.py` -- Added CustomProviderConfig, updated InfrastructureConfig.custom type
- `src/rsf/providers/__init__.py` -- Added CustomProvider import, registration, __all__ entry

## Conclusion

Phase 54 goal fully achieved. All 3 success criteria verified. All 3 requirements covered. 61 new tests pass. No regressions in the 169-test provider suite.
