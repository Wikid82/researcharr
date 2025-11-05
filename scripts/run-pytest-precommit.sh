#!/usr/bin/env bash
set -euo pipefail

# Run pytest with the repository root on PYTHONPATH so tests importing
# top-level modules (e.g., `import backups`) work when invoked from
# pre-commit hooks.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"

echo "Running pytest in pre-commit wrapper (PYTHONPATH=$PYTHONPATH)"
# default args: -q --maxfail=1, enable CLI logging at DEBUG and show extra
pytest -q --maxfail=1 -o log_cli=true -o log_cli_level=DEBUG -rA
