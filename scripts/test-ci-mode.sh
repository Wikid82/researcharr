#!/bin/bash
# Run tests with coverage exactly as CI does
# This prepends site-packages to PYTHONPATH to prefer the installed package
# over local source files, which changes import resolution and coverage calculation.

set -euo pipefail

# Detect site-packages for the chosen interpreter (same as CI)
SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
echo "Using site-packages: $SITE_PACKAGES"

# Prepend site-packages to PYTHONPATH (CI behavior)
export PYTHONPATH="$SITE_PACKAGES:${PYTHONPATH:-}"

# Run tests and produce coverage reports (same args as CI)
python -m pytest tests/ \
  --maxfail=3 --disable-warnings -v \
  --cov=researcharr --cov-report=xml:coverage.xml \
  --cov-report=term-missing \
  --cov-report=html \
  --junitxml=junit.xml -o junit_family=legacy

echo ""
echo "================================"
echo "Coverage report generated matching CI environment"
echo "Expected coverage: ~59% (matches CI)"
echo "Local mode without PYTHONPATH gives: ~64%"
echo "================================"
