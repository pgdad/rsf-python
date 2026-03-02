# Phase 43: Operational CLI Commands - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Three new CLI commands for operational workflows around deployed RSF infrastructure:
- `rsf logs` — tail and search correlated CloudWatch logs across all workflow Lambdas
- `rsf doctor` — diagnose environment and project health with pass/fail report
- `rsf export --format cloudformation` — generate deployable SAM templates from workflow definitions

Creating new infrastructure, modifying the DSL, or changing deployment behavior are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Log display & filtering
- Structured colored output: each line shows [timestamp] [function-name] [level] message
- Color coding by log level: green=INFO, yellow=WARN, red=ERROR (similar to docker-compose logs)
- `--tail` mode uses continuous polling at 2-3 second intervals, Ctrl+C to stop
- Filtering options: `--since` (duration like 1h or ISO date), `--level` (ERROR/WARN/INFO)
- `--execution-id <id>` correlates log lines across all Lambda functions in the workflow
- Lambda function discovery via Terraform state (same pattern as `rsf inspect --tf-dir`)

### Doctor check scope
- Check presence AND version compatibility: Python >=3.10, Terraform >=1.0, etc.
- Report format: PASS with version, WARN if outdated, FAIL if missing
- Actionable fix hints on failure (e.g., "Install: brew install terraform or https://terraform.io")
- Project-level checks when run inside a project directory: workflow.yaml exists/valid, terraform/ present, handlers/ present
- Rich checklist display with colored checkmarks/crosses

### Export format & fidelity
- Generate SAM (AWS::Serverless::Function) templates, not raw CloudFormation
- Full infrastructure export: Lambda, IAM roles/policies, CloudWatch log groups, triggers (EventBridge/SQS/SNS), DynamoDB tables, alarms, DLQ
- Output should be directly deployable via `sam build && sam deploy`
- Default output to stdout (pipeable), `--output` flag to write to file
- Workflow path as positional argument: `rsf export workflow.yaml`

### Cross-command UX
- `--json` flag for machine-readable output on `rsf logs` (JSONL format) and `rsf doctor` (JSON report)
- Auto-detect non-TTY and disable colors; also support explicit `--no-color` flag (Rich force_terminal)
- Workflow file as positional argument (default: workflow.yaml) — matches rsf validate, rsf deploy pattern
- Shared `--tf-dir` flag (default: terraform/) for Terraform state discovery — consistent with deploy and inspect

### Claude's Discretion
- Exact polling implementation and deduplication strategy for log tailing
- CloudWatch API pagination approach
- SAM template structure and resource naming conventions
- How to handle workflows with no Terraform state (graceful error messages)
- Doctor check ordering and grouping

</decisions>

<specifics>
## Specific Ideas

- Log output should feel like docker-compose logs — familiar multi-service log tailing with color-coded source labels
- Doctor should be a one-stop health check: both environment readiness and project validity
- SAM export should enable migration away from Terraform if desired — complete and deployable

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Rich Console` (all CLI commands): Used for colored output, Status spinners, error formatting
- `typer` framework: All commands follow Typer patterns with Options/Arguments
- `TerraformConfig` dataclass (`src/rsf/terraform/generator.py`): Full infrastructure model (Lambda, IAM, CloudWatch, triggers, DynamoDB, alarms, DLQ) — export can read this to know what resources exist
- Jinja2 template engine (`src/rsf/terraform/engine.py`): Could be reused for SAM template generation
- `rsf inspect` ARN discovery pattern (`src/rsf/cli/inspect_cmd.py`): Terraform state reading via `terraform output`

### Established Patterns
- Command file naming: `src/rsf/cli/{name}_cmd.py` with function registered in `main.py`
- Error handling: `[red]Error:[/red]` messages + `typer.Exit(code=1)`
- Progress indication: `rich.status.Status` for spinner feedback
- Workflow loading: `rsf.dsl.parser.load_definition(workflow)` for full DSL model
- Flag patterns: `--tf-dir` for Terraform directory, positional `workflow` argument

### Integration Points
- `main.py`: Register new commands via `app.command(name="logs")(logs_cmd.logs)` etc.
- `rsf.dsl.parser`: Load workflow definitions for export command
- `rsf.terraform.generator.TerraformConfig`: Read infrastructure model for export
- CloudWatch Logs API (boto3): New integration for `rsf logs`
- `shutil.which()`: Tool presence checks for doctor (already used for terraform in deploy_cmd)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 43-operational-cli-commands*
*Context gathered: 2026-03-02*
