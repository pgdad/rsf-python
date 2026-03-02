# S3 Event Pipeline Template

A complete RSF workflow that processes files uploaded to S3 through a validation, transformation, archival, and notification pipeline.

## Architecture

```
S3 Upload Event --> Lambda (RSF Orchestrator) --> Pipeline
   |
   +--> ValidateFile    --> Check extension + size
   +--> CheckValidation --> Branch: valid or invalid
   |    +--> valid:     --> TransformData --> ProcessUpload --> NotifyComplete --> Done
   |    +--> invalid:   --> NotifyFailure --> Failed
```

## Pipeline States

- **ValidateFile** -- Checks the uploaded file's extension and size against configurable limits
- **CheckValidation** -- Routes to transform (valid) or failure notification (invalid)
- **TransformData** -- Downloads the file, transforms it (CSV to JSON lines, JSON enrichment), uploads to `processed/`
- **ProcessUpload** -- Archives the original file by moving it to `archived/`
- **NotifyComplete** -- Sends success notification via SNS with processing summary
- **NotifyFailure** -- Sends failure notification via SNS with rejection reason

## Quick Start

```bash
# Scaffold the project
rsf init --template s3-event-pipeline my-pipeline

# Enter the project directory
cd my-pipeline

# Validate the workflow
rsf validate

# Generate orchestrator code and Terraform
rsf generate

# Deploy to AWS
rsf deploy
```

## Customization

### File Validation Rules

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_BUCKET` | `uploads` | Source S3 bucket name |
| `MAX_FILE_SIZE` | `52428800` (50MB) | Maximum file size in bytes |
| `ALLOWED_EXTENSIONS` | `.csv,.json,.parquet` | Comma-separated allowed extensions |
| `SNS_TOPIC_ARN` | _(empty)_ | SNS topic ARN for notifications |

### Adding New Transformations

Edit `handlers/transform_data.py` to add transformations for new file types. The current implementation handles:
- `.csv` -- Converts to JSON lines (`.jsonl`)
- `.json` -- Enriches with processing metadata
- Other -- Passes through unchanged

### Custom Archive Behavior

Edit `handlers/process_upload.py` to change archiving behavior (e.g., different prefix, retention policy, cross-region copy).

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

# Deploy (creates S3 bucket, SNS topic, Lambda functions)
rsf deploy

# Deploy to a specific stage
rsf deploy --stage prod
```
