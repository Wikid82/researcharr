#!/usr/bin/env bash
# Run BasedPyright (preferred) or pyright for pre-commit. The script will
# prefer a local binary if available, otherwise it will fall back to `npx`.

set -euo pipefail

if command -v based-pyright >/dev/null 2>&1; then
  exec based-pyright "$@"
fi

if command -v pyright >/dev/null 2>&1; then
  exec pyright "$@"
fi

# Try npx (no-install) for developer machines with Node/npm available.
if command -v npx >/dev/null 2>&1; then
  # Run pyright via npx when a local/global binary isn't available.
  exec npx --no-install pyright "$@"
fi

echo "Error: neither based-pyright, pyright, nor npx were available in PATH." >&2
exit 2
