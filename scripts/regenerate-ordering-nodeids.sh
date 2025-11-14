#!/usr/bin/env bash
set -euo pipefail

# Regenerate ordering_nodeids.txt containing full pytest nodeids (file::testname)
cd "$(dirname "$0")/.." || exit 1
# ensure writable location
OUT_FILE=ordering_nodeids.txt
echo "Regenerating $OUT_FILE (full pytest nodeids)"
# Use pytest collect-only to list nodeids. Use env to disable plugins that may alter collection.
RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
  pytest --collect-only -q > "$OUT_FILE"
echo "Wrote $OUT_FILE (lines: $(wc -l < "$OUT_FILE"))"
