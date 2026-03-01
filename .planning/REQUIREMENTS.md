# Requirements: RSF — Lambda Function URL Support

**Defined:** 2026-03-01
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.7 Requirements

Requirements for Lambda Function URL support. Each maps to roadmap phases.

### DSL (Workflow Definition)

- [ ] **DSL-01**: User can add optional `lambda_url` configuration to workflow YAML with `enabled: true` and `auth_type: NONE|AWS_IAM`
- [ ] **DSL-02**: DSL validation accepts lambda_url configuration and rejects invalid auth types

### Terraform (Infrastructure Generation)

- [ ] **TF-01**: When lambda_url is enabled, Terraform generation includes `aws_lambda_function_url` resource with configured auth type
- [ ] **TF-02**: Generated Terraform outputs include the Lambda Function URL endpoint
- [ ] **TF-03**: IAM policy includes necessary permissions when Lambda URL uses AWS_IAM auth

### Example (Demonstration Workflow)

- [ ] **EX-01**: New example workflow demonstrates triggering durable execution via Lambda Function URL POST
- [ ] **EX-02**: Example includes local tests verifying handler logic without AWS
- [ ] **EX-03**: Example includes integration test for Lambda URL invocation on real AWS

### Tutorial (Documentation)

- [ ] **TUT-01**: New tutorial covers Lambda URL configuration in workflow YAML and Terraform deployment
- [ ] **TUT-02**: Tutorial demonstrates invoking durable execution via curl POST to Lambda URL

## Future Requirements

None — this is a focused feature milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| API Gateway integration | Lambda URL is the simpler HTTP trigger; API Gateway is a separate feature |
| Custom domain for Lambda URL | Would require ACM certificate and Route53 setup; out of scope for v1 |
| Lambda URL CORS configuration | Can be added later; basic trigger functionality first |
| Request/response payload transformation | Lambda URL passes payload directly; no transform layer needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DSL-01 | Phase 36 | Pending |
| DSL-02 | Phase 36 | Pending |
| TF-01 | Phase 36 | Pending |
| TF-02 | Phase 36 | Pending |
| TF-03 | Phase 36 | Pending |
| EX-01 | Phase 37 | Pending |
| EX-02 | Phase 37 | Pending |
| EX-03 | Phase 37 | Pending |
| TUT-01 | Phase 38 | Pending |
| TUT-02 | Phase 38 | Pending |

**Coverage:**
- v1.7 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after roadmap creation (traceability complete)*
