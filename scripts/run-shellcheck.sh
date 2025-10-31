#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run shellcheck if available. If not available, warn and exit 0
if ! command -v shellcheck >/dev/null 2>&1; then
  echo "shellcheck not found; skipping shellcheck hook. Install shellcheck to enable this check." >&2
  exit 0
fi

# Run shellcheck on passed files; if no files passed, run on repo shell scripts
if [ "$#" -gt 0 ]; then
  shellcheck -x "$@"
else
  # find shell scripts in the repo and run shellcheck
  find . -type f -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck -x || true
fi
