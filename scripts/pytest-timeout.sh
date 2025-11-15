#!/usr/bin/env bash
set -euo pipefail

# Default timeout in seconds (override via PYTEST_TIMEOUT env var)
TIMEOUT_SECONDS="${PYTEST_TIMEOUT:-1800}"

# Prefer workspace venv python if available
PY_BIN="${PYTHON_BIN:-python}"
if [[ -x ".venv/bin/python" ]]; then
  PY_BIN=".venv/bin/python"
fi

# Run pytest under timeout, forwarding all arguments
exec timeout "${TIMEOUT_SECONDS}s" "${PY_BIN}" -m pytest "$@"
