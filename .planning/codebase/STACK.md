# Technology Stack

**Analysis Date:** 2026-03-11

## Languages

**Primary:**
- Python 3.12+ - Core CLI, server, and library code
- TypeScript 5.9 - UI (React) and VS Code extension

**Secondary:**
- JavaScript/Node.js - Build tooling, VS Code extension runtime

## Runtime

**Environment:**
- Python 3.12 (minimum requirement specified in `pyproject.toml`)
- Node.js - Used for Vite, esbuild, and VS Code extension bundling
- CPython with asyncio for async operations

**Package Manager:**
- pip (via `pyproject.toml` with hatchling build backend)
- npm - For UI and VS Code extension dependencies

## Frameworks

**Core Python:**
- FastAPI 0.100+ - REST API and WebSocket server
- Typer 0.9+ - CLI framework (entry point in `src/rsf/cli/main.py`)
- Pydantic 2.0+ - Data validation and serialization
- Uvicorn 0.20+ - ASGI server for FastAPI apps

**Frontend:**
- React 19.2+ - UI framework for graph editor and inspector
- Vite 7.3+ - Development server and build tool (`ui/vite.config.ts`)
- TypeScript 5.9+ - Type safety for UI code

**Editor & Language Server:**
- VS Code Language Server Protocol 9.0+ - Language server for workflow validation
- esbuild 0.20+ - Extension bundling (CommonJS, ES2020 target)
- Vite 7.3+ - React SPA build output to `src/rsf/editor/static/`

**Data Processing:**
- PyYAML 6.0+ - Workflow YAML parsing and serialization
- Jinja2 3.1+ - Template engine for infrastructure code generation

**Testing:**
- pytest 7.0+ - Test runner configured in `pyproject.toml` at `tests/`
- pytest-asyncio 0.21+ - Async test support
- Hypothesis 6.0+ - Property-based testing (optional dependency)
- Vitest 4.0+ (UI), 1.2+ (VS Code extension) - JavaScript test runners
- Playwright 1.58+ - Browser automation for E2E testing

**Infrastructure Provisioning:**
- Terraform (external) - Default infrastructure provider via `npx aws-cdk@latest`
- AWS CDK (invoked via npm) - Alternative infrastructure provider

**Build/Dev:**
- Hatchling - Python package build backend with VCS version support
- Ruff 3.x - Python linting and formatting (configured in `pyproject.toml`)
- ESLint 9.39+ - JavaScript/TypeScript linting (`ui/eslint.config.js` using flat config)

**Observability:**
- OpenTelemetry API 1.20+ - Optional tracing (in `[tracing]` extras)
- OpenTelemetry SDK 1.20+ - Optional instrumentation
- Rich 13.0+ - Terminal output formatting and styling
- Python logging module - Built-in logging framework

**File Watching:**
- watchfiles 0.20+ - File system monitoring for watch mode (optional dependency)

## Key Dependencies

**Critical:**
- boto3 1.28+ - AWS SDK for Lambda, CloudWatch Logs, IAM inspection
- fastapi 0.100+ - Request handling, WebSocket, SSE streaming
- pydantic 2.0+ - Workflow DSL model validation, type safety
- pyyaml 6.0+ - Workflow YAML deserialization

**Infrastructure & Deployment:**
- jinja2 3.1+ - Generate Terraform/CDK code from templates
- typer 0.9+ - CLI argument parsing and subcommand routing

**Server & Async:**
- uvicorn[standard] 0.20+ - ASGI server with uvloop, websockets, httptools
- sse-starlette 1.0+ - Server-Sent Events streaming for live execution updates

**React & UI:**
- @monaco-editor/react 4.7+ - Code editor for YAML editing
- @xyflow/react 12.10+ - Interactive graph visualization (node-edge diagram)
- zustand 5.0+ - State management (lightweight alternative to Redux)
- js-yaml 4.1+ - YAML parsing in browser
- immer 11.1+ - Immutable state updates

**Testing & Development:**
- httpx 0.24+ - Async HTTP client for testing FastAPI routes
- @testing-library/react 16.3+ - Component testing utilities

## Configuration

**Environment:**
- AWS credentials resolved via boto3 session (standard AWS SDK credential chain)
- Region via boto3 default region or explicit `region_name` parameter
- No `.env` file loading mechanism detected; uses environment variables directly

**Build:**
- `pyproject.toml` - Python project metadata, dependencies, pytest config, ruff settings
- `ui/tsconfig.json` - TypeScript references to `tsconfig.app.json` and `tsconfig.node.json`
- `ui/vite.config.ts` - Vite build output to `../src/rsf/editor/static/`
- `vscode-extension/esbuild.config.mjs` - Extension bundling (CommonJS, minified for production)
- `.prettierrc` - Not detected; no Prettier configuration
- ESLint config at `ui/eslint.config.js` - Flat config with React hooks, TypeScript, and Vite plugin
- Ruff configuration in `pyproject.toml` - Line length 120, rules E, F, W

## Platform Requirements

**Development:**
- Python 3.12 or 3.13
- Node.js (version not explicitly pinned in `package.json`)
- Terraform CLI (if using Terraform provider) or AWS CDK CLI (if using CDK provider)
- boto3-compatible AWS credentials

**Production:**
- AWS Lambda (target compute platform)
- AWS IAM roles with appropriate permissions for Lambda, CloudWatch Logs
- DynamoDB (for template examples `api-gateway-crud`, `s3-event-pipeline`)
- S3 (for template examples, SNS/SQS referenced in templates)
- API Gateway or Lambda URLs (for HTTP trigger)
- AWS CloudWatch Logs (execution visibility and monitoring)

## Supported Python Versions

- Python 3.12 (primary)
- Python 3.13 (supported via CI matrix in `.github/workflows/ci.yml`)

---

*Stack analysis: 2026-03-11*
