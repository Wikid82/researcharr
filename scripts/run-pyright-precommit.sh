#!/usr/bin/env bash
# Run BasedPyright (preferred) or pyright for pre-commit. The script will
# prefer a local binary if available, otherwise it will fall back to `npx`.
# Skip in CI if npx/pyright are unavailable.

set -euo pipefail

# Skip in CI if no pyright binary or npx is available
if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  if ! command -v based-pyright >/dev/null 2>&1 && \
     ! command -v pyright >/dev/null 2>&1 && \
     ! command -v npx >/dev/null 2>&1; then
    echo "Skipping basedpyright in CI (no binary/npx available)"
    exit 0
  fi
fi

if command -v based-pyright >/dev/null 2>&1; then
  exec based-pyright "$@"
fi

if command -v pyright >/dev/null 2>&1; then
  exec pyright "$@"
fi

# Try npx for developer machines and CI with Node/npm available.
if command -v npx >/dev/null 2>&1; then
  # Run pyright via npx when a local/global binary isn't available.
  exec npx pyright "$@"
fi

echo "Error: neither based-pyright, pyright, nor npx were available in PATH." >&2
exit 2
