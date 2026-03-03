---
phase: 53-cdk-provider
plan: 02
status: complete
---

# Plan 02: CDKProvider Class

## What Was Built
- **CDKProvider** (src/rsf/providers/cdk.py) implementing all 5 InfrastructureProvider abstract methods
- **generate()** delegates to generate_cdk with _build_config converting WorkflowMetadata to CDKConfig
- **deploy()** checks bootstrap first, then runs `npx aws-cdk@latest deploy` with streaming output
- **teardown()** runs `npx aws-cdk@latest destroy --force` with streaming output
- **check_prerequisites()** returns FAIL for missing npx, WARN for missing cdk binary
- **run_provider_command_streaming()** streams stdout/stderr directly to terminal (no capture_output)
- **_check_bootstrap_or_warn()** detects missing CDKToolkit stack via boto3 cloudformation
- **_get_account_and_region()** via boto3 STS for bootstrap command messaging

## Key Decisions
- Used `npx aws-cdk@latest` instead of global cdk binary (no global install needed)
- Streaming subprocess for deploy/teardown so users see CDK stack events in real-time
- Bootstrap detection via CloudFormation describe_stacks rather than cdk ls
- Module-level boto3 import for testability (patch("rsf.providers.cdk.boto3") works)
- CDK binary is WARN (not FAIL) since npx handles CDK execution

## Test Results
- 21 tests passing across 7 test classes
- No regressions in existing test suite

## Key Files
- `src/rsf/providers/cdk.py` — CDKProvider implementation
- `tests/test_providers/test_cdk_provider.py` — comprehensive tests

## Self-Check: PASSED
- [x] CDKProvider implements all 5 InfrastructureProvider abstract methods
- [x] deploy() invokes npx aws-cdk@latest deploy with streaming output
- [x] deploy() checks CDK bootstrap before running cdk deploy
- [x] deploy() maps auto_approve to --require-approval never
- [x] deploy() passes stage as CDK context value -c stage=X
- [x] teardown() invokes npx aws-cdk@latest destroy --force
- [x] check_prerequisites() returns FAIL for missing npx, WARN for missing cdk
- [x] Bootstrap detection uses boto3 cloudformation.describe_stacks
- [x] All tests pass
