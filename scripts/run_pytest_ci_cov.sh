#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root from this script's location
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="${SCRIPT_DIR%/scripts}"

# Prefer venv python if available
if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate"
fi

# Compute site-packages path using the active interpreter
SITE_PACKAGES="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
export PYTHONPATH="${SITE_PACKAGES}:${PYTHONPATH:-}"

# Run pytest with coverage like CI
exec python -m pytest tests/ --cov=researcharr --cov-report=term-missing --cov-report=html --cov-report=xml
