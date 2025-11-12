#!/usr/bin/env bash
set -euo pipefail

# Local helper to run tests and pre-commit hooks similar to GitHub Actions CI.
# Usage: ./scripts/run-local-ci.sh

echo "Running CI-like checks locally..."

# Activate the project's venv if present
if [ -f .venv/bin/activate ]; then
  echo "Activating .venv..."
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi

echo "Running pre-commit hooks..."
pre-commit run --all-files

echo "Running pytest with coverage (CI-like)..."
# Prepend site-packages so pytest prefers the installed package over top-level modules
SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
echo "Using site-packages: $SITE_PACKAGES"
export PYTHONPATH="$SITE_PACKAGES:$PYTHONPATH"

pytest tests/ \
  --maxfail=3 --disable-warnings -v \
  --cov=researcharr --cov-report=xml:coverage.xml \
  --junitxml=junit.xml -o junit_family=legacy

echo "Local CI run complete. Coverage written to coverage.xml; junit to junit.xml."
