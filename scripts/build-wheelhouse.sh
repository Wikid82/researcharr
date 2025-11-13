#!/usr/bin/env bash
set -euo pipefail

# Helper to build a local wheelhouse for development.
# By default this builds pure Python wheels via `pip wheel` which is fast and
# works for development. If you pass `--cibuildwheel` it will attempt to run
# `cibuildwheel` (requires Docker / manylinux setup).

OUTDIR="wheelhouse"
USE_CIBW=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cibuildwheel)
      USE_CIBW=true
      shift
      ;;
    --out|--output)
      OUTDIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--cibuildwheel] [--out DIR]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$OUTDIR"

if [ "$USE_CIBW" = true ]; then
  if ! command -v cibuildwheel >/dev/null 2>&1; then
    echo "cibuildwheel not found; install it with: python -m pip install cibuildwheel" >&2
    exit 1
  fi
  echo "Running cibuildwheel (this may take a while)..."
  cibuildwheel --output-dir "$OUTDIR"
else
  echo "Building wheelhouse with pip (fast local dev path) into: $OUTDIR"
  python -m pip install --upgrade pip setuptools wheel
  python -m pip wheel -w "$OUTDIR" -r requirements.txt
fi

echo "Wheelhouse ready at: $OUTDIR"
