#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run pytest in the same way CI does (ensure installed package
# in site-packages is preferred). Intended to be used by pre-commit pre-push hook.

SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="${SITE_PACKAGES}:${PYTHONPATH:-}"

exec pytest tests/ --maxfail=1 -q
