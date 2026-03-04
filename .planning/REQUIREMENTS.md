# Requirements: RSF v3.2 — Terraform Registry Modules Tutorial

**Defined:** 2026-03-03
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v3.2 Requirements

Requirements for the Terraform Registry Modules Tutorial milestone. Each maps to roadmap phases.

### Custom Provider Script

- [ ] **PROV-01**: Custom provider Python script reads WorkflowMetadata via FileTransport and invokes terraform apply
- [ ] **PROV-02**: rsf.toml configures provider="custom" with absolute path, FileTransport, and teardown_args
- [ ] **PROV-03**: Deploy script handles both deploy and teardown via command dispatch argument
- [ ] **PROV-04**: Deploy script zips RSF-generated source before terraform apply (resolves packaging conflict)

### Registry Modules

- [ ] **REG-01**: Lambda deployed via terraform-aws-modules/lambda/aws with durable_config and create_package=false
- [ ] **REG-02**: DynamoDB table deployed via terraform-aws-modules/dynamodb-table/aws
- [ ] **REG-03**: SQS DLQ deployed via terraform-aws-modules/sqs/aws conditionally based on dlq_enabled
- [ ] **REG-04**: CloudWatch alarms deployed via terraform-aws-modules/cloudwatch metric-alarm submodule
- [ ] **REG-05**: SNS topic deployed via terraform-aws-modules/sns/aws for alarm notifications
- [ ] **REG-06**: All registry module versions pinned to exact versions in versions.tf

### Example

- [ ] **EXAM-01**: New example workflow YAML with Task states, DynamoDB table, and DLQ configuration
- [ ] **EXAM-02**: Example follows RSF directory convention (workflow.yaml, handlers/, tests/, terraform/, README.md)
- [ ] **EXAM-03**: Example handlers implement business logic with structured logging

### Testing

- [ ] **TEST-01**: Local unit tests verify workflow parsing, handler registration, and handler execution
- [ ] **TEST-02**: Integration test deploys to AWS, invokes durable execution, polls for SUCCEEDED, verifies logs
- [ ] **TEST-03**: Integration test performs clean teardown via custom provider teardown path

### Tutorial

- [ ] **TUT-01**: Step-by-step tutorial (tutorials/09-custom-provider-registry-modules.md) walks through custom provider creation
- [ ] **TUT-02**: Tutorial includes side-by-side comparison of raw HCL vs registry module HCL
- [ ] **TUT-03**: Tutorial includes annotated WorkflowMetadata schema table for provider authors
- [ ] **TUT-04**: Tutorial covers pitfalls: absolute path, chmod +x, packaging conflict, version pinning, durable IAM

### Tooling

- [ ] **TOOL-01**: Fix custom provider friction points discovered during tutorial development (if any)

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Alternative IaC Tutorials

- **ALT-01**: Pulumi registry module tutorial (equivalent to this milestone but for Pulumi)
- **ALT-02**: CDK Construct Hub tutorial (equivalent for CDK constructs)
- **ALT-03**: Multi-provider composition tutorial (Terraform + custom in one workflow)

### Custom Provider SDK

- **SDK-01**: Python SDK/base class for custom provider authors (beyond subprocess model)
- **SDK-02**: All three metadata transport deep-dive tutorial (File, Env, Args)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New RSF DSL syntax for registry modules | Registry modules are a Terraform concept; RSF stays IaC-agnostic |
| Auto-generating registry module HCL from RSF | Would bake terraform-aws-modules into RSF core; defeats provider abstraction |
| Pulumi or CDK registry equivalents | One complete tutorial is better than three partial ones |
| Custom Terraform module authoring/publishing | Publishing to Terraform Registry is a different skill |
| Serverless Framework or SAM equivalent | Different tools, different audiences |
| Multi-provider composition in one workflow | Complex; single provider per workflow is the supported model |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | — | Pending |
| PROV-02 | — | Pending |
| PROV-03 | — | Pending |
| PROV-04 | — | Pending |
| REG-01 | — | Pending |
| REG-02 | — | Pending |
| REG-03 | — | Pending |
| REG-04 | — | Pending |
| REG-05 | — | Pending |
| REG-06 | — | Pending |
| EXAM-01 | — | Pending |
| EXAM-02 | — | Pending |
| EXAM-03 | — | Pending |
| TEST-01 | — | Pending |
| TEST-02 | — | Pending |
| TEST-03 | — | Pending |
| TUT-01 | — | Pending |
| TUT-02 | — | Pending |
| TUT-03 | — | Pending |
| TUT-04 | — | Pending |
| TOOL-01 | — | Pending |

**Coverage:**
- v3.2 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after initial definition*
