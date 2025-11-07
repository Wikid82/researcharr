#!/usr/bin/env bash
set -euo pipefail

# Run pytest with the repository root on PYTHONPATH so tests importing
# top-level modules (e.g., `import backups`) work when invoked from
# pre-commit hooks.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"

echo "Running pytest in pre-commit wrapper (PYTHONPATH=$PYTHONPATH)"
# If a project virtualenv exists, prefer its python by prepending its bin
# directory to PATH. This makes the `python -m pytest` invocation below use
# the project's venv when pre-commit is run from a different environment.
for venv_name in ".venv-3.13" ".venv" "venv"; do
	if [ -x "$REPO_ROOT/$venv_name/bin/python" ]; then
		export PATH="$REPO_ROOT/$venv_name/bin:$PATH"
		break
	fi
done

# default args: -q --maxfail=1, enable CLI logging at DEBUG and show extra
# Use --full-trace in pre-commit to produce complete tracebacks for easier
# debugging of import-time shims and hook-invoked failures. This mirrors CI
# verbosity and helps triage failures earlier in the pre-commit pipeline.
python -m pytest -q --maxfail=1 -o log_cli=true -o log_cli_level=DEBUG -rA --full-trace
