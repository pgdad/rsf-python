#!/usr/bin/env bash
# deploy.sh — RSF custom provider script for registry-modules-demo
# Invoked by RSF's CustomProvider with RSF_METADATA_FILE set via FileTransport.
# Usage:
#   deploy.sh deploy   — zip source + run terraform apply
#   deploy.sh destroy  — run terraform destroy

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths — always compute from script location, never from $PWD
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/terraform"
BUILD_DIR="${SCRIPT_DIR}/build"
METADATA_FILE="${RSF_METADATA_FILE}"
TFVARS_FILE="${TF_DIR}/terraform.tfvars.json"

# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
CMD="${1:-deploy}"

# ---------------------------------------------------------------------------
# Banner — extract workflow_name from metadata for display only
# ---------------------------------------------------------------------------
WORKFLOW_NAME="$(jq -r '.workflow_name' "${METADATA_FILE}")"

echo "=== registry-modules-demo deploy.sh ==="
echo "Command          : ${CMD}"
echo "Workflow name    : ${WORKFLOW_NAME}"
echo ""

# ---------------------------------------------------------------------------
# generate_tfvars — generate terraform.tfvars.json from RSF_METADATA_FILE.
# Called from BOTH deploy and destroy branches (Pitfall 5: tfvars must exist
# for destroy even when build artifacts are absent).
# ---------------------------------------------------------------------------
generate_tfvars() {
  jq -n \
    --argjson metadata "$(cat "${METADATA_FILE}")" \
    '{
      workflow_name:         $metadata.workflow_name,
      execution_timeout:     ($metadata.timeout_seconds // 86400),
      dynamodb_tables:       ($metadata.dynamodb_tables // []),
      dlq_enabled:           ($metadata.dlq_enabled // false),
      dlq_queue_name:        $metadata.dlq_queue_name,
      dlq_max_receive_count: ($metadata.dlq_max_receive_count // 3),
      alarms:                [($metadata.alarms // [])[] | {type, threshold, period, evaluation_periods}]
    }' > "${TFVARS_FILE}"
  echo "Generated: ${TFVARS_FILE}"
}

case "${CMD}" in
  deploy)
    # -----------------------------------------------------------------------
    # Step 1: Package — zip RSF-generated orchestrator + handler files
    # -----------------------------------------------------------------------
    mkdir -p "${BUILD_DIR}"
    cd "${SCRIPT_DIR}"
    zip -r "${BUILD_DIR}/function.zip" src/generated/ handlers/ \
      -x "**/__pycache__/*" "**/*.pyc"
    echo "Packaged: ${BUILD_DIR}/function.zip"
    echo ""

    # -----------------------------------------------------------------------
    # Step 2: Generate terraform.tfvars.json from RSF metadata
    # -----------------------------------------------------------------------
    generate_tfvars

    # -----------------------------------------------------------------------
    # Step 3: Terraform — init + apply
    # -----------------------------------------------------------------------
    cd "${TF_DIR}"
    terraform init -input=false
    terraform apply -auto-approve \
      -var-file="${TFVARS_FILE}"

    # -----------------------------------------------------------------------
    # Step 4: Print alias ARN with sample invocation command
    # -----------------------------------------------------------------------
    ALIAS_ARN="$(terraform output -raw alias_arn)"
    echo ""
    echo "=== Deploy complete ==="
    echo "Alias ARN: ${ALIAS_ARN}"
    echo ""
    echo "Sample invocation:"
    echo "  aws lambda invoke \\"
    echo "    --function-name '${ALIAS_ARN}' \\"
    echo "    --payload '{\"image_url\": \"s3://my-bucket/photo.jpg\"}' \\"
    echo "    --cli-binary-format raw-in-base64-out \\"
    echo "    response.json && cat response.json"
    ;;

  destroy)
    # -----------------------------------------------------------------------
    # Step 1: Generate terraform.tfvars.json from RSF metadata
    # (required even for destroy — Terraform needs variable values)
    # -----------------------------------------------------------------------
    generate_tfvars

    # -----------------------------------------------------------------------
    # Step 2: Terraform — init + destroy
    # -----------------------------------------------------------------------
    cd "${TF_DIR}"
    terraform init -input=false
    terraform destroy -auto-approve \
      -var-file="${TFVARS_FILE}"
    echo ""
    echo "Teardown complete."
    ;;

  *)
    echo "Unknown command: ${CMD}. Use 'deploy' or 'destroy'." >&2
    exit 1
    ;;
esac
