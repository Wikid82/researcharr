#!/usr/bin/env bash
set -euo pipefail

# Run pre-commit inside a project-local virtualenv (.venv)
# - Creates .venv if missing
# - Installs dev requirements (if present) or pre-commit
# - Runs pre-commit across the repo
# - Exits non-zero if hooks made changes (so CI/local flows can detect)

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENV_DIR="$ROOT_DIR/.venv"

echo "Using project root: $ROOT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck source=/dev/null
. "$VENV_DIR/bin/activate"

echo "Upgrading pip and installing pre-commit (or requirements-dev.txt)"
python -m pip install --upgrade pip >/dev/null
if [ -f "$ROOT_DIR/requirements-dev.txt" ]; then
  pip install -r "$ROOT_DIR/requirements-dev.txt"
else
  pip install pre-commit >/dev/null
fi

echo "Running pre-commit hooks (this may modify files)..."
# Use python -m pre_commit to ensure it runs from the venv
python -m pre_commit run --all-files --show-diff-on-failure || true

if [ -n "$(git status --porcelain)" ]; then
  echo "pre-commit made changes. Please review, commit and push them."
  git status --porcelain
  exit 1
fi

echo "pre-commit completed with no changes."

# Optional: run tests with coverage when --with-tests is supplied.
if [[ "${1:-}" == "--with-tests" ]]; then
  echo "Running test suite with coverage (optional step)..."
  SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
  export PYTHONPATH="$SITE_PACKAGES:$PYTHONPATH"
  python -m pytest tests/ --cov=researcharr --cov-report=term-missing --cov-report=html --cov-report=xml || exit 1
fi

exit 0
