#!/usr/bin/env bash
# RSF GitHub Action entrypoint — installs RSF and runs validate/generate/deploy pipeline.
set -euo pipefail

# ─── Install RSF ─────────────────────────────────────────────────────────────

echo "::group::Installing RSF"
if [ -n "${RSF_INSTALL_SOURCE:-}" ]; then
    echo "Installing RSF from custom source: ${RSF_INSTALL_SOURCE}"
    pip install "${RSF_INSTALL_SOURCE}"
elif [ "${RSF_VERSION:-latest}" = "latest" ]; then
    echo "Installing latest RSF from PyPI"
    pip install rsf
else
    echo "Installing RSF version ${RSF_VERSION}"
    pip install "rsf==${RSF_VERSION}"
fi
echo "RSF version: $(rsf --version)"
echo "::endgroup::"

# ─── Validate ────────────────────────────────────────────────────────────────

echo "::group::Validating workflow"
VALIDATE_OUTPUT=""
VALIDATE_RESULT="pass"

if VALIDATE_OUTPUT=$(rsf validate "${WORKFLOW_FILE}" 2>&1); then
    echo "Validation passed"
    VALIDATE_RESULT="pass"
else
    echo "Validation failed"
    VALIDATE_RESULT="fail"
fi

# Set outputs (multiline-safe)
{
    echo "validate-result=${VALIDATE_RESULT}"
    echo "validate-output<<GH_EOF"
    echo "${VALIDATE_OUTPUT}"
    echo "GH_EOF"
} >> "$GITHUB_OUTPUT"

echo "::endgroup::"

# Stop if validation failed
if [ "${VALIDATE_RESULT}" = "fail" ]; then
    echo "::error::Workflow validation failed. See output for details."
    # Still exit 0 to allow comment posting
    GENERATE_RESULT="skipped"
    DEPLOY_RESULT="skipped"
    {
        echo "generate-result=${GENERATE_RESULT}"
        echo "generate-output=Skipped (validation failed)"
        echo "deploy-result=${DEPLOY_RESULT}"
        echo "deploy-output=Skipped (validation failed)"
    } >> "$GITHUB_OUTPUT"
    exit 0
fi

# ─── Generate ────────────────────────────────────────────────────────────────

echo "::group::Generating code"
GENERATE_OUTPUT=""
GENERATE_RESULT="pass"

if GENERATE_OUTPUT=$(rsf generate "${WORKFLOW_FILE}" 2>&1); then
    echo "Generation passed"
    GENERATE_RESULT="pass"
else
    echo "Generation failed"
    GENERATE_RESULT="fail"
fi

{
    echo "generate-result=${GENERATE_RESULT}"
    echo "generate-output<<GH_EOF"
    echo "${GENERATE_OUTPUT}"
    echo "GH_EOF"
} >> "$GITHUB_OUTPUT"

echo "::endgroup::"

# ─── Deploy (opt-in) ─────────────────────────────────────────────────────────

DEPLOY_OUTPUT=""
DEPLOY_RESULT="skipped"

if [ "${DEPLOY}" = "true" ] && [ "${GENERATE_RESULT}" = "pass" ]; then
    echo "::group::Deploying workflow"
    DEPLOY_CMD="rsf deploy"

    if [ -n "${STAGE:-}" ]; then
        DEPLOY_CMD="${DEPLOY_CMD} --stage ${STAGE}"
    fi

    if [ "${AUTO_APPROVE}" = "true" ]; then
        DEPLOY_CMD="${DEPLOY_CMD} --auto-approve"
    fi

    if DEPLOY_OUTPUT=$(eval "${DEPLOY_CMD}" 2>&1); then
        echo "Deploy passed"
        DEPLOY_RESULT="pass"
    else
        echo "Deploy failed"
        DEPLOY_RESULT="fail"
    fi

    echo "::endgroup::"
fi

{
    echo "deploy-result=${DEPLOY_RESULT}"
    echo "deploy-output<<GH_EOF"
    echo "${DEPLOY_OUTPUT}"
    echo "GH_EOF"
} >> "$GITHUB_OUTPUT"

echo "RSF Action complete: validate=${VALIDATE_RESULT} generate=${GENERATE_RESULT} deploy=${DEPLOY_RESULT}"
