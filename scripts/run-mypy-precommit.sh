#!/usr/bin/env bash
# Run mypy using the project's venv python when available so pre-commit's
# system hook observes the same installed typing stubs developers use.
# Falls back to plain `python -m mypy` if the expected venv is absent.

set -euo pipefail

VENV_PY=".venv-3.13/bin/python"
if [ -x "$VENV_PY" ]; then
  exec "$VENV_PY" -m mypy "$@"
else
  exec python -m mypy "$@"
fi
