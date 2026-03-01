# Requirements: RSF v2.0

**Defined:** 2026-03-01
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v2.0 Requirements

Requirements for v2.0 release. Each maps to roadmap phases.

### CLI Enhancements

- [ ] **CLI-01**: User can run `rsf diff` to see structural differences between local workflow definition and deployed state
- [ ] **CLI-02**: User can run `rsf test` to execute a workflow locally with a given input payload, printing state transitions and final output
- [ ] **CLI-03**: User can run `rsf watch` to auto-validate and re-generate on file changes, with optional `--deploy` for code-only updates
- [ ] **CLI-04**: User can run `rsf logs` to tail/search CloudWatch logs across all Lambda functions in a workflow, correlated by execution ID
- [ ] **CLI-05**: User can run `rsf doctor` to diagnose Python version, Terraform, AWS credentials, and SDK availability
- [ ] **CLI-06**: User can run `rsf export --format cloudformation` to generate CloudFormation/SAM templates from workflow definitions

### DSL & Core

- [ ] **DSL-01**: User can configure EventBridge rules, SQS queues, and SNS subscriptions as workflow trigger sources in the DSL
- [ ] **DSL-02**: User can invoke one workflow from another as a nested sub-workflow call
- [ ] **DSL-03**: User can define DynamoDB tables in the DSL with auto-generated Terraform and IAM permissions
- [ ] **DSL-04**: User can define CloudWatch Alarms (error rate, duration, throttle) in the DSL with SNS notification Terraform
- [ ] **DSL-05**: User can configure dead letter queues for Lambda functions that exhaust all retries
- [ ] **DSL-06**: User can set a top-level workflow timeout that terminates the entire execution if exceeded
- [ ] **DSL-07**: User can deploy to multiple stages (dev/staging/prod) via `--stage` with stage-specific variable files

### Infrastructure

- [ ] **INFRA-01**: User can generate workflow code and handlers without any Terraform/AWS resource generation, making infrastructure creation fully optional

### Observability

- [ ] **OBS-01**: Generated orchestrator code includes OpenTelemetry trace context injection for distributed tracing
- [ ] **OBS-02**: User can run `rsf cost` to estimate monthly AWS costs based on workflow structure and expected invocation count
- [ ] **OBS-03**: An example workflow demonstrates CloudWatch custom metrics with a Grafana dashboard JSON

### UI & Inspector

- [ ] **UI-01**: User can replay a workflow execution from the inspector UI with the same or modified input payload
- [ ] **UI-02**: RSF's workflow.yaml JSON Schema is published to SchemaStore for automatic IDE auto-complete

### Testing

- [ ] **TEST-01**: Property-based tests (hypothesis) verify I/O pipeline invariants across randomly generated inputs and JSONPath expressions
- [ ] **TEST-02**: Test utilities inject failures (timeout, exception, throttle) into specific states during local test runs
- [ ] **TEST-03**: Snapshot tests capture full generated orchestrator.py for each example, catching code generation regressions

### Ecosystem

- [ ] **ECO-01**: VS Code extension provides YAML schema validation, go-to-definition for state references, and inline graph preview
- [ ] **ECO-02**: `rsf init --template <name>` scaffolds from curated workflow templates (api-gateway-crud, s3-event-pipeline, etc.)
- [ ] **ECO-03**: Reusable GitHub Action (`rsf-action`) validates, generates, and deploys workflows in CI with plan output as PR comments

## Future Requirements

Deferred beyond v2.0. Tracked but not in current roadmap.

- **FUT-01**: Go or other language runtime support
- **FUT-02**: Team collaboration features (multi-user editing)
- **FUT-03**: Hosted web service with authentication
- **FUT-04**: Mobile app
- **FUT-05**: LocalStack / moto mocking (Lambda Durable Functions not supported)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Java port | Moved to separate rsf-java repo |
| Direct AWS Console integration | Operates independently from Console |
| Real-time chat/collaboration | Local-first tool, no multi-user |
| Parallel CI test execution | Need cost and timing data first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 42 | Pending |
| CLI-02 | Phase 42 | Pending |
| CLI-03 | Phase 42 | Pending |
| CLI-04 | Phase 43 | Pending |
| CLI-05 | Phase 43 | Pending |
| CLI-06 | Phase 43 | Pending |
| DSL-01 | Phase 40 | Pending |
| DSL-02 | Phase 40 | Pending |
| DSL-03 | Phase 40 | Pending |
| DSL-04 | Phase 41 | Pending |
| DSL-05 | Phase 41 | Pending |
| DSL-06 | Phase 39 | Pending |
| DSL-07 | Phase 41 | Pending |
| INFRA-01 | Phase 39 | Pending |
| OBS-01 | Phase 44 | Pending |
| OBS-02 | Phase 44 | Pending |
| OBS-03 | Phase 44 | Pending |
| UI-01 | Phase 46 | Pending |
| UI-02 | Phase 46 | Pending |
| TEST-01 | Phase 45 | Pending |
| TEST-02 | Phase 45 | Pending |
| TEST-03 | Phase 45 | Pending |
| ECO-01 | Phase 48 | Pending |
| ECO-02 | Phase 47 | Pending |
| ECO-03 | Phase 47 | Pending |

**Coverage:**
- v2.0 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 — traceability complete after v2.0 roadmap creation*
