# Lambda URL Trigger

A webhook receiver workflow demonstrating how to trigger a durable execution via HTTP POST to a Lambda Function URL.

## DSL Features Demonstrated

| Feature | Usage |
|---------|-------|
| **Task** | ValidateOrder, ProcessOrder |
| **Succeed** | OrderComplete terminal state |
| **Lambda URL** | `lambda_url: {enabled: true, auth_type: NONE}` — public HTTP endpoint |

## Workflow Path

```
HTTP POST → Lambda URL → ValidateOrder → ProcessOrder → OrderComplete
```

## Run Locally (No AWS)

```bash
pytest examples/lambda-url-trigger/tests/test_local.py -v
```

## Run Integration Test (AWS)

```bash
pytest tests/test_examples/test_lambda_url_trigger.py -m integration -v
```
