# Requirements: RSF v1.2

**Defined:** 2026-02-26
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.2 Requirements

Requirements for the Comprehensive Examples & Integration Testing milestone. Each maps to roadmap phases.

### Example Workflows

- [ ] **EXAM-01**: User can deploy an order-processing example demonstrating Task, Choice, Parallel, Succeed, and Fail states with Retry/Catch error handling
- [ ] **EXAM-02**: User can deploy a data-pipeline example demonstrating Task, Pass, and Map states with DynamoDB service integration and I/O processing
- [ ] **EXAM-03**: User can deploy an approval-workflow example demonstrating Task, Wait, Choice, and Pass states with Context Object ($$) and Variables/Assign
- [ ] **EXAM-04**: User can deploy a retry-and-recovery example demonstrating multi-Catch chains, JitterStrategy (FULL/NONE), BackoffRate, and MaxDelaySeconds
- [ ] **EXAM-05**: User can deploy an intrinsic-showcase example exercising 14+ intrinsic functions and all 5 I/O pipeline stages (InputPath, Parameters, ResultSelector, ResultPath, OutputPath)
- [ ] **EXAM-06**: Each example includes complete DSL YAML, Python handler implementations, and generated Terraform files
- [ ] **EXAM-07**: Each example handler emits structured JSON logs with step name and execution context
- [ ] **EXAM-08**: Each example includes a local mock SDK test that passes without AWS credentials

### Test Harness

- [ ] **HARN-01**: User can invoke poll_execution() to wait for durable execution completion with 3-5s polling interval and exponential backoff on throttle
- [ ] **HARN-02**: User can invoke query_logs() to verify CloudWatch logs with 15s propagation buffer and retry loop
- [ ] **HARN-03**: User can invoke teardown that runs terraform destroy and explicitly deletes orphaned CloudWatch log groups
- [ ] **HARN-04**: User can run full integration test suite with single command: `pytest tests/test_examples/ -m integration`
- [ ] **HARN-05**: Each example uses independent local Terraform state (no shared state files)
- [ ] **HARN-06**: Test harness generates UUID-suffixed execution IDs to prevent collisions across runs
- [ ] **HARN-07**: Test harness includes 15s IAM propagation buffer between terraform apply and first invocation

### Verification

- [ ] **VERF-01**: Each example verifies workflow correctness via Lambda return value assertion
- [ ] **VERF-02**: Each example verifies intermediate state transitions via CloudWatch log assertions
- [ ] **VERF-03**: All 8 state types are verified in real AWS execution across the example set

### Documentation

- [ ] **DOCS-01**: Each example includes a README documenting which DSL features it demonstrates and how to run it standalone
- [ ] **DOCS-02**: Top-level examples README with prerequisites (AWS credentials, Terraform, Python 3.13+) and quick-start guide

## Future Requirements

Deferred to v1.2.x or v2+. Tracked but not in current roadmap.

### CI/CD

- **CICD-01**: GitHub Actions workflow to run integration tests on push/PR
- **CICD-02**: Parallel CI execution of integration tests across examples

### Additional Examples

- **ADDL-01**: SQS integration example demonstrating message queue patterns
- **ADDL-02**: S3 integration example demonstrating file processing patterns

### Local Testing

- **LOCL-01**: LocalStack support for offline integration testing (pending durable execution compatibility)

## Out of Scope

| Feature | Reason |
|---------|--------|
| LocalStack / moto mocking of durable functions | Lambda Durable Functions (re:Invent 2025) not supported by either framework |
| Parallel CI test execution | Need cost and timing data from sequential runs first |
| Every individual operator tested separately | 39 operators covered by operator families in examples + existing v1.0 unit tests |
| Every intrinsic function in deployed examples | 14/18 covered in deployed examples; remaining 4 (Base64Encode, Base64Decode, Hash, UUID) covered by v1.0 unit tests |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXAM-01 | Phase 13 | Pending |
| EXAM-02 | Phase 13 | Pending |
| EXAM-03 | Phase 13 | Pending |
| EXAM-04 | Phase 13 | Pending |
| EXAM-05 | Phase 13 | Pending |
| EXAM-06 | Phase 14 | Pending |
| EXAM-07 | Phase 13 | Pending |
| EXAM-08 | Phase 13 | Pending |
| HARN-01 | Phase 15 | Pending |
| HARN-02 | Phase 15 | Pending |
| HARN-03 | Phase 15 | Pending |
| HARN-04 | Phase 15 | Pending |
| HARN-05 | Phase 14 | Pending |
| HARN-06 | Phase 15 | Pending |
| HARN-07 | Phase 15 | Pending |
| VERF-01 | Phase 16 | Pending |
| VERF-02 | Phase 16 | Pending |
| VERF-03 | Phase 16 | Pending |
| DOCS-01 | Phase 17 | Pending |
| DOCS-02 | Phase 17 | Pending |

**Coverage:**
- v1.2 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after roadmap creation — all 20 requirements mapped to phases 13-17*
