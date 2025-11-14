#!/usr/bin/env bash
# Run BasedPyright (preferred) or pyright for pre-commit. The script will
# prefer a local binary if available, otherwise it will fall back to `npx`.
# Skip in CI if pyright is unavailable.

set -euo pipefail

# In CI, skip if no local binaries are available (npx often fails with incomplete packages)
if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  if ! command -v based-pyright >/dev/null 2>&1 && \
     ! command -v pyright >/dev/null 2>&1; then
    echo "Skipping basedpyright in CI (no local binary available)"
    exit 0
  fi
fi

if command -v based-pyright >/dev/null 2>&1; then
  exec based-pyright "$@"
fi

if command -v pyright >/dev/null 2>&1; then
  exec pyright "$@"
fi

# Try npx for developer machines with Node/npm available (skip in CI).
if command -v npx >/dev/null 2>&1; then
  # Run pyright via npx when a local/global binary isn't available.
  exec npx pyright "$@"
fi

echo "Error: neither based-pyright, pyright, nor npx were available in PATH." >&2
exit 2
