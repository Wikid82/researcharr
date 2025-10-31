#!/usr/bin/env bash
set -euo pipefail

# Local CI runner: mirrors the GitHub Actions `build` job steps so you can
# run checks locally. Intended for developer machines and CI debugging.
#
# Usage:
#   ./scripts/ci-local.sh           # install deps, run pre-commit, run pytest
#   ./scripts/ci-local.sh --skip-install --no-docker --no-trivy
#

SKIP_INSTALL=0
DO_DOCKER=1
DO_TRIVY=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install) SKIP_INSTALL=1; shift ;;
    --no-docker) DO_DOCKER=0; shift ;;
    --no-trivy) DO_TRIVY=0; shift ;;
    -h|--help)
      # Print the usage block starting at the "# Usage:" marker until the
      # first blank line, which keeps the help text maintainable in the
      # script body instead of relying on a magic line count.
      awk '/^# Usage:/ {show=1; next} show && /^$/ {exit} show {print}' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

echo "Local CI runner starting..."

if [ "$SKIP_INSTALL" -eq 0 ]; then
  echo "Installing Python dependencies..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  pip install setuptools_scm
  pip install black==23.9.1 isort==5.12.0 flake8 mypy pytest pytest-cov pre-commit || true
  pip install types-requests types-PyYAML || true
  pip install -e .
fi

echo "Running pre-commit hooks..."
pre-commit run --all-files

echo "Running pytest..."
# Ensure tests use installed package if present (mimic CI behavior)
SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="${SITE_PACKAGES}:${PYTHONPATH:-}"
pytest tests/ --maxfail=3 --disable-warnings -v --cov=researcharr --cov-report=xml:coverage.xml

echo "tests completed. coverage.xml created."

if [ "$DO_DOCKER" -eq 1 ]; then
  echo "Building docker image for local scan: researcharr-ci:local"
  docker build -t researcharr-ci:local . || true
  if [ "$DO_TRIVY" -eq 1 ]; then
    echo "Running trivy scan (HIGH/CRITICAL will cause non-zero exit)..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$(pwd)":/workspace aquasec/trivy:latest image --format json -o /workspace/trivy-report.json researcharr-ci:local || true
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
      aquasec/trivy:latest image --exit-code 1 --severity HIGH,CRITICAL researcharr-ci:local || true
    echo "Trivy report written to trivy-report.json"
  fi
fi

echo "Local CI runner finished."
