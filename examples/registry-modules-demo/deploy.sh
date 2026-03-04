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

# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
CMD="${1:-deploy}"

# ---------------------------------------------------------------------------
# Metadata extraction via jq (FileTransport writes WorkflowMetadata as JSON)
# ---------------------------------------------------------------------------
WORKFLOW_NAME="$(jq -r '.workflow_name' "${METADATA_FILE}")"
EXECUTION_TIMEOUT="$(jq -r '.timeout_seconds // 86400' "${METADATA_FILE}")"

echo "=== registry-modules-demo deploy.sh ==="
echo "Command          : ${CMD}"
echo "Workflow name    : ${WORKFLOW_NAME}"
echo "Execution timeout: ${EXECUTION_TIMEOUT}s"
echo ""

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
    # Step 2: Terraform — init + apply
    # -----------------------------------------------------------------------
    cd "${TF_DIR}"
    terraform init -input=false
    terraform apply -auto-approve \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="execution_timeout=${EXECUTION_TIMEOUT}"

    # -----------------------------------------------------------------------
    # Step 3: Print alias ARN with sample invocation command
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
    # Terraform — init + destroy
    # -----------------------------------------------------------------------
    cd "${TF_DIR}"
    terraform init -input=false
    terraform destroy -auto-approve \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="execution_timeout=${EXECUTION_TIMEOUT}"
    echo ""
    echo "Teardown complete."
    ;;

  *)
    echo "Unknown command: ${CMD}. Use 'deploy' or 'destroy'." >&2
    exit 1
    ;;
esac
