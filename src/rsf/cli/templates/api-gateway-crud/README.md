# API Gateway CRUD Template

A complete RSF workflow that implements a DynamoDB-backed REST API with full CRUD operations routed through API Gateway.

## Architecture

```
API Gateway --> Lambda (RSF Orchestrator) --> DynamoDB
   |
   +--> POST   /items       --> CreateItem handler --> DynamoDB put_item
   +--> GET    /items/{id}  --> GetItem handler    --> DynamoDB get_item
   +--> GET    /items       --> ListItems handler  --> DynamoDB scan
   +--> PUT    /items/{id}  --> UpdateItem handler --> DynamoDB update_item
   +--> DELETE /items/{id}  --> DeleteItem handler --> DynamoDB delete_item
```

## Workflow States

The workflow routes incoming HTTP requests to the appropriate CRUD handler based on the HTTP method:

- **RouteRequest** — Choice state that routes by `httpMethod` (POST, GET, PUT, DELETE)
- **CheckSingleItem** — Choice state that distinguishes GET single item vs. list
- **CreateItem** — Creates a new item with a generated UUID
- **GetItem** — Retrieves a single item by ID (returns 404 if not found)
- **UpdateItem** — Updates item fields using DynamoDB update expressions
- **DeleteItem** — Removes an item by ID
- **ListItems** — Scans the table with pagination support

## Quick Start

```bash
# Scaffold the project
rsf init --template api-gateway-crud my-api

# Enter the project directory
cd my-api

# Validate the workflow
rsf validate

# Generate orchestrator code and Terraform
rsf generate

# Deploy to AWS
rsf deploy
```

## Customization

### Changing the Table Schema

Edit `workflow.yaml` to add new states, or modify handlers to work with different DynamoDB attribute schemas. The default schema uses a single `id` (String) hash key.

### Adding Fields

1. Update handler files in `handlers/` to include new fields in put/update operations
2. Update `terraform.tf.j2` if you need additional DynamoDB indexes (GSI/LSI)
3. Update tests in `tests/test_handlers.py` to cover the new fields

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DYNAMODB_TABLE` | `Items` | DynamoDB table name |

## Testing

```bash
# Run unit tests (mocks boto3, no AWS credentials needed)
pytest tests/

# Run with verbose output
pytest tests/ -v
```

## Deployment

```bash
# Validate workflow definition
rsf validate

# Generate code + Terraform
rsf generate

# Deploy (creates DynamoDB table + Lambda functions)
rsf deploy

# Deploy to a specific stage
rsf deploy --stage prod
```
