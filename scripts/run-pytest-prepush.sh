#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run pytest in the same way CI does (ensure installed package
# in site-packages is preferred). Intended to be used by pre-commit pre-push hook.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# If a virtualenv exists in the repo, prefer it so pytest runs with the
# same dependencies developers use locally.
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
	# shellcheck disable=SC1091
	. "$REPO_ROOT/.venv/bin/activate"
fi

# Use the active python's site-packages so installed editable/package deps
# are discoverable similar to CI.
SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="${SITE_PACKAGES}:${PYTHONPATH:-}"

exec pytest tests/ --maxfail=1 -q
