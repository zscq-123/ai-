#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAVA_HOME_VALUE="${JAVA_HOME:-/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home}"
PYTHON_VALUE="${PYTHON_BIN:-${PROJECT_ROOT}/.venv/bin/python}"

cd "${PROJECT_ROOT}"
pnpm lint
pnpm typecheck
pnpm build
pnpm --filter admin build-storybook
JAVA_HOME="${JAVA_HOME_VALUE}" services/commerce-api/mvnw -f services/commerce-api/pom.xml -B verify
"${PYTHON_VALUE}" -m ruff check services/ai-service
"${PYTHON_VALUE}" -m mypy services/ai-service/src
"${PYTHON_VALUE}" -m pytest services/ai-service
docker compose --env-file .env.example -f docker-compose.yml -f infra/compose/production.yml config --quiet
