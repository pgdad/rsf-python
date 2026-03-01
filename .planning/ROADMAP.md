# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- ✅ **v1.4 UI Screenshots** — Phases 21-24 (shipped 2026-02-27)
- ✅ **v1.5 PyPI Packaging & Distribution** — Phases 25-27 (shipped 2026-02-28)
- ✅ **v1.6 Ruff Linting Cleanup** — Phases 28-35 (shipped 2026-03-01)
- ✅ **v1.7 Lambda Function URL Support** — Phases 36-38 (shipped 2026-03-01)
- 📋 **v2.0 Comprehensive Enhancement Suite** — Phases 39-48 (planned)

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-11) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: DSL Core (5/5 plans) — completed 2026-02-25
- [x] Phase 2: Code Generation (3/3 plans) — completed 2026-02-25
- [x] Phase 3: Terraform Generation (2/2 plans) — completed 2026-02-25
- [x] Phase 4: ASL Importer (2/2 plans) — completed 2026-02-25
- [x] Phase 6: Graph Editor Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Graph Editor UI (5/5 plans) — completed 2026-02-25
- [x] Phase 8: Inspector Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 9: Inspector UI (5/5 plans) — completed 2026-02-25
- [x] Phase 10: Testing (9/9 plans) — completed 2026-02-25
- [x] Phase 11: Documentation (4/4 plans) — completed 2026-02-25

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 CLI Toolchain (Phase 12) — SHIPPED 2026-02-26</summary>

- [x] Phase 12: CLI Toolchain (4/4 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Comprehensive Examples & Integration Testing (Phases 13-17) — SHIPPED 2026-02-26</summary>

- [x] Phase 13: Example Foundation (5/5 plans) — completed 2026-02-26
- [x] Phase 14: Terraform Infrastructure (1/1 plan) — completed 2026-02-26
- [x] Phase 15: Integration Test Harness (1/1 plan) — completed 2026-02-26
- [x] Phase 16: AWS Deployment and Verification (1/1 plan) — completed 2026-02-26
- [x] Phase 17: Cleanup and Documentation (1/1 plan) — completed 2026-02-26

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Comprehensive Tutorial (Phases 18-20) — SHIPPED 2026-02-26</summary>

- [x] Phase 18: Getting Started (2/2 plans) — completed 2026-02-26
- [x] Phase 19: Build and Deploy (3/3 plans) — completed 2026-02-26
- [x] Phase 20: Advanced Tools (3/3 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 UI Screenshots (Phases 21-24) — SHIPPED 2026-02-27</summary>

- [x] Phase 21: Playwright Setup (1/1 plan) — completed 2026-02-26
- [x] Phase 22: Mock Fixtures and Server Automation (2/2 plans) — completed 2026-02-27
- [x] Phase 23: Screenshot Capture (1/1 plan) — completed 2026-02-27
- [x] Phase 24: Documentation Integration (1/1 plan) — completed 2026-02-27

Full details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

<details>
<summary>✅ v1.5 PyPI Packaging & Distribution (Phases 25-27) — SHIPPED 2026-02-28</summary>

- [x] Phase 25: Package & Version (1/1 plan) — completed 2026-02-28
- [x] Phase 26: CI/CD Pipeline (1/1 plan) — completed 2026-02-28
- [x] Phase 27: README as Landing Page (1/1 plan) — completed 2026-02-28

Full details: `.planning/milestones/v1.5-ROADMAP.md`

</details>

<details>
<summary>✅ v1.6 Ruff Linting Cleanup (Phases 28-35) — SHIPPED 2026-03-01</summary>

- [x] Phase 28: F401 Unused Imports (2/2 plans) — completed 2026-02-28
- [x] Phase 29: F841 Unused Variables — completed 2026-02-28
- [x] Phase 30: F541 f-string Without Placeholders — completed 2026-02-28
- [x] Phase 31: E402 Import Not at Top of File — completed 2026-02-28
- [x] Phase 32: E741 Ambiguous Variable Names — completed 2026-02-28
- [x] Phase 33: E501 Line Too Long — completed 2026-02-28
- [x] Phase 34: Config Cleanup — completed 2026-02-28
- [x] Phase 35: Run All Tests That Do Not Require AWS Access/Resources (1/1 plan) — completed 2026-03-01

</details>

<details>
<summary>✅ v1.7 Lambda Function URL Support (Phases 36-38) — SHIPPED 2026-03-01</summary>

- [x] Phase 36: DSL and Terraform (2/2 plans) — completed 2026-03-01
- [x] Phase 37: Example Workflow (3/3 plans) — completed 2026-03-01
- [x] Phase 38: Tutorial (1/1 plan) — completed 2026-03-01

Full details: `.planning/milestones/v1.7-ROADMAP.md`

</details>

### 📋 v2.0 Comprehensive Enhancement Suite (Phases 39-48)

**Milestone Goal:** Expand RSF from a code generation toolkit into a full development platform with new CLI commands, event triggers, observability, testing utilities, IDE integration, and optional infrastructure generation.

- [x] **Phase 39: Infrastructure Decoupling and Workflow Timeout** — Make Terraform generation optional and add top-level workflow timeout to the DSL (completed 2026-03-01)
- [ ] **Phase 40: Event Triggers, Sub-Workflows, and DynamoDB** — Extend the DSL with event source triggers, nested workflow invocation, and DynamoDB table definitions
- [ ] **Phase 41: Alerts, Dead Letter Queues, and Multi-Stage Deploy** — Add operational DSL extensions for CloudWatch alarms, Lambda DLQs, and stage-based deployments
- [ ] **Phase 42: Developer CLI Commands** — Add `rsf diff`, `rsf test`, and `rsf watch` for local development iteration
- [ ] **Phase 43: Operational CLI Commands** — Add `rsf logs`, `rsf doctor`, and `rsf export` for deployment and operations support
- [ ] **Phase 44: Observability** — Add OpenTelemetry tracing, cost estimation CLI, and a CloudWatch metrics dashboard example
- [ ] **Phase 45: Advanced Testing Utilities** — Add property-based, chaos, and snapshot testing capabilities
- [ ] **Phase 46: Inspector Replay and SchemaStore** — Enable execution replay from the inspector UI and publish the DSL schema to SchemaStore
- [ ] **Phase 47: Workflow Templates and GitHub Action** — Add `rsf init --template` scaffolding and a reusable `rsf-action` GitHub Action
- [ ] **Phase 48: VS Code Extension** — Deliver YAML schema validation, go-to-definition, and inline graph preview in VS Code

## Phase Details

### Phase 39: Infrastructure Decoupling and Workflow Timeout
**Goal**: Users can generate workflow code without any Terraform output, and can set an execution timeout that terminates the entire workflow if exceeded
**Depends on**: Phase 38 (v1.7 complete)
**Requirements**: INFRA-01, DSL-06
**Success Criteria** (what must be TRUE):
  1. User can run `rsf generate` without any Terraform files being created when infrastructure generation is disabled
  2. A `--no-infra` flag (or equivalent config) separates code generation from infrastructure generation
  3. User can add a top-level `timeout` field to workflow.yaml and the generated orchestrator enforces it
  4. Running `rsf validate` reports an error when timeout value is invalid or out of range
**Plans**: TBD

### Phase 40: Event Triggers, Sub-Workflows, and DynamoDB
**Goal**: Users can configure EventBridge, SQS, and SNS as workflow triggers, invoke child workflows from a parent, and define DynamoDB tables directly in the DSL
**Depends on**: Phase 39
**Requirements**: DSL-01, DSL-02, DSL-03
**Success Criteria** (what must be TRUE):
  1. User can declare EventBridge rules, SQS queues, or SNS subscriptions as trigger sources in workflow.yaml and `rsf generate` produces the corresponding Terraform
  2. User can reference a child workflow by name inside a parent workflow state and the generated code invokes it as a durable sub-execution
  3. User can define DynamoDB table schemas in workflow.yaml and `rsf generate` produces Terraform table definitions with correct IAM permissions
  4. `rsf validate` catches invalid trigger configurations and unknown sub-workflow references before code generation
**Plans**: TBD

### Phase 41: Alerts, Dead Letter Queues, and Multi-Stage Deploy
**Goal**: Users can define CloudWatch alarms and Lambda dead letter queues in the DSL, and deploy to named stages with stage-specific variable overrides
**Depends on**: Phase 40
**Requirements**: DSL-04, DSL-05, DSL-07
**Success Criteria** (what must be TRUE):
  1. User can declare CloudWatch error-rate, duration, and throttle alarms in workflow.yaml and `rsf generate` produces Terraform alarm resources with SNS notification targets
  2. User can configure a dead letter queue for any Lambda function in the workflow and the generated Terraform wires up the SQS DLQ and IAM permissions
  3. User can run `rsf deploy --stage prod` and the deploy uses a prod-specific variable file, keeping dev and prod infrastructure isolated
  4. Stage-specific variable files override the base configuration without modifying core workflow definition files
**Plans**: TBD

### Phase 42: Developer CLI Commands
**Goal**: Users can compare local and deployed workflow state, run workflows locally with full trace output, and watch for file changes to auto-validate and re-generate
**Depends on**: Phase 41
**Requirements**: CLI-01, CLI-02, CLI-03
**Success Criteria** (what must be TRUE):
  1. User can run `rsf diff` and see a structured diff showing which states, transitions, or handler signatures have changed between local workflow.yaml and the deployed Lambda code
  2. User can run `rsf test --input '{"key":"value"}'` and see each state transition printed with its input, output, and handler result as the workflow executes locally
  3. User can run `rsf watch` and any change to workflow.yaml or handler files triggers automatic validation and code generation within a few seconds
  4. User can run `rsf watch --deploy` and successful validation also triggers a `--code-only` Lambda update automatically
**Plans**: TBD

### Phase 43: Operational CLI Commands
**Goal**: Users can tail and search correlated CloudWatch logs, diagnose environment problems, and export workflows to CloudFormation format
**Depends on**: Phase 42
**Requirements**: CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. User can run `rsf logs --execution-id <id>` and see log lines from all Lambda functions in the workflow correlated by that execution ID
  2. User can run `rsf logs --tail` and see a continuous stream of new log events across all workflow Lambdas
  3. User can run `rsf doctor` and receive a pass/fail report for Python version, Terraform binary, AWS credential validity, and SDK availability
  4. User can run `rsf export --format cloudformation` and receive a CloudFormation/SAM template equivalent of the workflow's Terraform infrastructure
**Plans**: TBD

### Phase 44: Observability
**Goal**: Generated orchestrators carry OpenTelemetry trace context, users can estimate workflow costs before deploying, and a dashboard example demonstrates custom CloudWatch metrics
**Depends on**: Phase 43
**Requirements**: OBS-01, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. Generated orchestrator.py includes OpenTelemetry context injection so distributed traces appear in any compatible backend (Jaeger, X-Ray, etc.) when the workflow executes
  2. User can run `rsf cost --invocations 10000` and receive an estimated monthly cost breakdown by Lambda invocations, DynamoDB reads/writes, and data transfer
  3. An example workflow ships with CloudWatch custom metric emissions and a Grafana dashboard JSON that can be imported to visualize execution counts, durations, and error rates
**Plans**: TBD

### Phase 45: Advanced Testing Utilities
**Goal**: The RSF test suite covers I/O pipeline invariants with property-based tests, supports chaos injection for state failures, and snapshots generated orchestrator code to catch regressions
**Depends on**: Phase 39
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Hypothesis-based property tests run as part of the standard pytest suite and verify that the 5-stage I/O pipeline produces valid output for any randomly generated input and JSONPath expression
  2. Test utilities expose a `inject_failure(state_name, failure_type)` API that causes a specific state to raise a timeout, exception, or throttle error during local test runs
  3. Snapshot tests compare the full text of generated orchestrator.py for each example workflow against committed golden files, and the CI pipeline fails if any generated output changes unexpectedly
**Plans**: TBD

### Phase 46: Inspector Replay and SchemaStore
**Goal**: Users can replay any past execution from the inspector UI with the same or modified payload, and RSF's workflow schema is available for automatic IDE auto-complete via SchemaStore
**Depends on**: Phase 44
**Requirements**: UI-01, UI-02
**Success Criteria** (what must be TRUE):
  1. User can select a completed execution in the inspector, click Replay, optionally edit the input payload, and trigger a new execution that appears immediately in the inspector
  2. RSF's workflow.yaml JSON Schema is published to the SchemaStore GitHub repository and IDEs that support SchemaStore automatically validate and auto-complete workflow.yaml files
  3. Schema auto-complete covers all DSL fields added through v2.0 (triggers, sub-workflows, DynamoDB, alarms, DLQ, timeout, stages)
**Plans**: TBD

### Phase 47: Workflow Templates and GitHub Action
**Goal**: Users can scaffold new projects from curated workflow templates, and CI pipelines can validate, generate, and deploy workflows using a reusable GitHub Action
**Depends on**: Phase 43
**Requirements**: ECO-02, ECO-03
**Success Criteria** (what must be TRUE):
  1. User can run `rsf init --template api-gateway-crud` and receive a complete project scaffold with workflow.yaml, handlers, tests, and Terraform pre-configured for that pattern
  2. At least two named templates ship (e.g., `api-gateway-crud` and `s3-event-pipeline`), each with a working example and documentation
  3. A GitHub Action (`rsf-action`) is available on the GitHub Actions Marketplace that runs validate, generate, and optionally deploy, posting a plan summary as a PR comment
  4. The GitHub Action works without pre-installing RSF — it handles setup internally
**Plans**: TBD

### Phase 48: VS Code Extension
**Goal**: VS Code users get YAML schema validation, go-to-definition for state references, and an inline graph preview panel for workflow.yaml files
**Depends on**: Phase 46
**Requirements**: ECO-01
**Success Criteria** (what must be TRUE):
  1. Opening a workflow.yaml in VS Code shows real-time validation errors and warnings sourced from the RSF Pydantic schema, matching `rsf validate` output
  2. Pressing go-to-definition on a state name (e.g., in a `Next` or `Default` field) navigates to the target state's definition within the same file
  3. A VS Code panel shows a live graph preview of the current workflow that updates as the user edits workflow.yaml
  4. The extension is installable from the VS Code Marketplace and works without any local RSF installation
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → 47 → 48

Note: Phase 45 (Testing) depends only on Phase 39 and can be worked in parallel with Phases 40-44 if desired.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 39. Infrastructure Decoupling and Workflow Timeout | 2/2 | Complete   | 2026-03-01 |
| 40. Event Triggers, Sub-Workflows, and DynamoDB | 0/TBD | Not started | - |
| 41. Alerts, Dead Letter Queues, and Multi-Stage Deploy | 0/TBD | Not started | - |
| 42. Developer CLI Commands | 0/TBD | Not started | - |
| 43. Operational CLI Commands | 0/TBD | Not started | - |
| 44. Observability | 0/TBD | Not started | - |
| 45. Advanced Testing Utilities | 0/TBD | Not started | - |
| 46. Inspector Replay and SchemaStore | 0/TBD | Not started | - |
| 47. Workflow Templates and GitHub Action | 0/TBD | Not started | - |
| 48. VS Code Extension | 0/TBD | Not started | - |
