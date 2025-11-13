#!/usr/bin/env bash
# Quick CI-mode smoke test: mimic CI import path and run the fast smoke suite
# This prepends site-packages to PYTHONPATH to prefer the installed package
# and runs the lightweight smoke tests to catch packaging/import issues fast.
set -euo pipefail

# Clear developer triage env vars so the smoke hook behaves like CI
# Some developer workflows export these to disable pytest plugins for
# isolated debugging; unset them here so the pre-commit hook loads
# plugins (xdist, etc.) as CI expects.
unset PYTEST_DISABLE_PLUGIN_AUTOLOAD RESEARCHARR_DISABLE_PLUGINS || true

# Resolve a Python interpreter robustly across environments
PY="${PYTHON:-}"
if [[ -z "${PY}" ]]; then
	if [[ -x ".venv/bin/python" ]]; then
		PY=".venv/bin/python"
		PATH=".venv/bin:${PATH}"
	elif command -v python >/dev/null 2>&1; then
		PY=python
	elif command -v python3 >/dev/null 2>&1; then
		PY=python3
	else
		echo "ERROR: python interpreter not found (tried .venv/bin/python, python, python3)" >&2
		exit 127
	fi
fi

SITE_PACKAGES=$("${PY}" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="$SITE_PACKAGES:${PYTHONPATH:-}"

# Use the same smoke target as Docker images
"${PY}" -m pytest -q tests/run/test_run.py --maxfail=1 --disable-warnings
