# Phase 60: Tutorial Document - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Create tutorials/09-custom-provider-registry-modules.md — a step-by-step tutorial that walks a developer new to RSF's custom provider system from prerequisites through a working real-AWS deployment using Terraform registry modules, with side-by-side HCL comparison, annotated WorkflowMetadata schema table, and common pitfalls section. The tutorial documents the existing registry-modules-demo example built in Phases 56-59.

</domain>

<decisions>
## Implementation Decisions

### Tutorial structure
- Linear walkthrough: Prerequisites → Project setup → Custom provider config → Deploy script → Terraform → Deploy → Verify → Understand architecture → Pitfalls → Teardown
- Reference the existing examples/registry-modules-demo/ files — reader clones the repo and follows along (not type-from-scratch)
- Side-by-side HCL comparison and schema table appear AFTER deploy succeeds — "Now let's understand what just happened"
- Coarse granularity: 8-12 numbered steps, each covering a logical phase (matches tutorial 04 density)

### Side-by-side HCL comparison (TUT-02)
- Consecutive labeled code blocks: "RSF TerraformProvider output (raw HCL):" then "Registry module equivalent:" — works in all markdown renderers
- Compare Lambda AND DynamoDB resources (satisfies "at least Lambda and DynamoDB" requirement)
- Include IAM differences as a callout box after the Lambda comparison — highlights raw aws_iam_role vs module-created role
- Raw HCL sourced from RSF's Jinja2 templates (src/rsf/terraform/templates/main.tf.j2, dynamodb.tf.j2)
- Registry module HCL sourced from examples/registry-modules-demo/terraform/main.tf, dynamodb.tf

### WorkflowMetadata schema table (TUT-03)
- 3-column markdown table: Field | Description | Example Value
- Cover the fields used in the example: workflow_name, timeout_seconds, dynamodb_tables, dlq_enabled, dlq_max_receive_count, dlq_queue_name, alarms
- Annotated with how each field maps to Terraform variables (the metadata → tfvars.json → Terraform pipeline)

### Common Pitfalls section (TUT-04)
- Dedicated section after the architecture explanation (not inline warnings)
- Each pitfall: Problem + Symptom (what error you see) + Fix
- Four required pitfalls:
  1. Absolute path requirement in rsf.toml program field
  2. chmod +x requirement for deploy.sh
  3. Packaging conflict (create_package=false + local_existing_package)
  4. Exact version pinning rationale (Terraform does not lock module versions)
  5. Durable IAM permissions not included in module defaults (hybrid approach required)

### Audience & tone
- Assumes reader completed tutorials 01-05 (knows workflow.yaml, rsf generate, rsf deploy with built-in Terraform)
- Assumes basic Terraform familiarity (has run terraform apply, understands resources/modules/variables)
- Direct and practical tone matching tutorials 01-08: imperative instructions, bash commands with expected output, brief "why" explanations
- "What You'll Learn" + "What You'll Build" text summary at top listing components (custom provider, deploy.sh, 5 registry modules)
- Cost warning matching tutorial 04 pattern

### Claude's Discretion
- Exact step numbering and step titles
- How much deploy.sh code to inline vs reference
- Whether to show full .tf file contents or excerpts with file path references
- Terraform output formatting in expected-output blocks
- How to present the metadata → tfvars.json → Terraform pipeline visually
- Exact wording of the "What You'll Learn" and "What You'll Build" sections
- Whether to include a "Next Steps" section at the end (future tutorials, advanced usage)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tutorials/04-deploy-to-aws.md`: Reference for structure, tone, prerequisites, cost warning format
- `examples/registry-modules-demo/`: Complete working example with all files the tutorial documents
- `src/rsf/terraform/templates/main.tf.j2`: Raw HCL Lambda template for side-by-side comparison
- `src/rsf/terraform/templates/dynamodb.tf.j2`: Raw HCL DynamoDB template for comparison
- `src/rsf/providers/metadata.py`: WorkflowMetadata dataclass source for schema table
- `examples/registry-modules-demo/terraform/main.tf`: Registry module Lambda HCL for comparison
- `examples/registry-modules-demo/terraform/dynamodb.tf`: Registry module DynamoDB HCL for comparison
- `examples/registry-modules-demo/deploy.sh`: Deploy script to walk through in tutorial
- `examples/registry-modules-demo/rsf.toml`: Custom provider config to explain
- `examples/registry-modules-demo/workflow.yaml`: Image processing workflow to reference

### Established Patterns
- Tutorials use "## What You'll Learn" with bullet list at top
- Tutorials use "## Prerequisites" with tool verification commands
- Steps are "## Step N: Title" with bash code blocks and expected output
- Cost warnings use `> **Cost warning:**` blockquote format
- Tutorials end with teardown step showing clean destruction

### Integration Points
- New file: `tutorials/09-custom-provider-registry-modules.md`
- References existing example files in `examples/registry-modules-demo/`
- Links back to tutorials 01-05 as prerequisites
- References RSF's TerraformProvider output templates for comparison

</code_context>

<specifics>
## Specific Ideas

- The "understand what happened" section after deploy is the tutorial's unique teaching moment — it's where the side-by-side comparison, schema table, and architecture explanation live
- The deploy step should show the actual deploy.sh banner output so readers know what to expect
- Each pitfall should include the exact error message or symptom a reader would see if they hit it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 60-tutorial-document*
*Context gathered: 2026-03-04*
