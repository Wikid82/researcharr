#!/usr/bin/env bash
set -euo pipefail

# Run Safety vulnerability scan as a pre-commit local hook.
# Prefer project venv Python if present, otherwise fall back to system python.
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
for v in ".venv-3.13" ".venv" "venv"; do
  if [ -x "$ROOT_DIR/$v/bin/python" ]; then
    PY="$ROOT_DIR/$v/bin/python"
    break
  fi
done

# Try modern Safety v3+ command first; fall back to deprecated 'check'.
# Exit non-zero on vulnerabilities so pre-commit can block the commit.
if "$PY" -m safety --help >/dev/null 2>&1; then
  if "$PY" -m safety scan --non-interactive --full-report; then
    exit 0
  else
    echo "Safety scan reported vulnerabilities." >&2
    exit 1
  fi
fi

# Fallback for environments where module invocation differs
if command -v safety >/dev/null 2>&1; then
  if safety scan --non-interactive --full-report; then
    exit 0
  else
    echo "Safety scan reported vulnerabilities." >&2
    exit 1
  fi
fi

echo "Safety is not installed. Install dev requirements to enable this hook (pip install -r requirements-dev.txt)." >&2
exit 0
