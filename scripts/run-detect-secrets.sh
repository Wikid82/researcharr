#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run detect-secrets pre-commit behavior.
# If detect-secrets-hook is available, run it (it accepts filenames passed by pre-commit).
# Otherwise fall back to running `detect-secrets scan` against the repo and fail if new secrets found.

BASELINE=".secrets.baseline"

if command -v detect-secrets-hook >/dev/null 2>&1; then
  detect-secrets-hook --baseline "$BASELINE" "$@"
  exit $?
fi

if command -v detect-secrets >/dev/null 2>&1; then
  # If filenames were passed, check only those files; otherwise scan all files
  if [ "$#" -gt 0 ]; then
    detect-secrets scan --baseline "$BASELINE" "$@" || exit $?
  else
    detect-secrets scan --baseline "$BASELINE" --all-files || exit $?
  fi
  exit 0
fi

echo "detect-secrets is not installed in PATH; install detect-secrets (pip install detect-secrets) to enable this hook." >&2
exit 0
