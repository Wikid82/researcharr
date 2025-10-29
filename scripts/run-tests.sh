#!/usr/bin/env bash
set -euo pipefail

# Helper script for CI/local runs to ensure tests run with the repo
# root on PYTHONPATH so top-level modules (e.g. factory.py) import
# correctly. Produces an XML coverage report suitable for Codecov.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

# Default PYTHONPATH to repo root if not set
if [ -z "${PYTHONPATH+x}" ]; then
  PYTHONPATH=.
fi
export PYTHONPATH

# Allow passing extra pytest args
pytest --cov=researcharr --cov-report=xml:coverage.xml "$@"
