# Plan 43-02 Summary: rsf doctor command

## Status: COMPLETE

## What was built
Environment and project health diagnostic command (`rsf doctor`) that checks Python version, Terraform binary, AWS credentials, boto3 SDK, and AWS CLI availability. Includes project-level checks for workflow.yaml, terraform/, and handlers/ directories. Outputs a colored checklist with fix hints, --json report, and appropriate exit codes.

## Key files
- `src/rsf/cli/doctor_cmd.py` — rsf doctor command implementation
- `src/rsf/cli/main.py` — CLI registration (doctor command added)
- `tests/test_cli/test_doctor.py` — 23 tests covering all check functions and CLI output

## Test results
23/23 tests passed

## Self-Check: PASSED
- [x] All tasks executed
- [x] Each task committed individually
- [x] Tests pass
- [x] Command registered in main.py
