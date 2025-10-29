#!/usr/bin/env bash
set -euo pipefail
# scripts/bootstrap-config.sh
# Copy example config files from the repository into a host `./config`
# directory and set ownership according to PUID/PGID environment variables.
# Usage: scripts/bootstrap-config.sh [target-dir]
# Default target-dir: ./config

TARGET_DIR=${1:-./config}
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC_CONFIG="$REPO_ROOT/config"

# Runtime ownership defaults (can be overridden by environment)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Bootstrapping config into: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
mkdir -p "$TARGET_DIR/plugins"

# Copy top-level config if missing
if [ -f "$SRC_CONFIG/config.yml" ]; then
  if [ ! -f "$TARGET_DIR/config.yml" ]; then
    cp "$SRC_CONFIG/config.yml" "$TARGET_DIR/config.yml"
    echo "Copied config.yml"
  else
    echo "config.yml already exists in $TARGET_DIR; skipping"
  fi
fi

# Copy plugin example files (do not overwrite existing)
if [ -d "$SRC_CONFIG/plugins" ]; then
  for f in "$SRC_CONFIG/plugins"/*; do
    bn=$(basename "$f")
    if [ ! -f "$TARGET_DIR/plugins/$bn" ]; then
      cp "$f" "$TARGET_DIR/plugins/$bn"
      echo "Copied plugins/$bn"
    else
      echo "plugins/$bn already exists; skipping"
    fi
  done
fi

# Ensure target ownership (best-effort)
if chown -R "${PUID}:${PGID}" "$TARGET_DIR" 2>/dev/null; then
  echo "Adjusted ownership to ${PUID}:${PGID}"
else
  echo "Warning: chown failed or not permitted; ensure $TARGET_DIR is writable by the container user"
fi

echo "Bootstrap complete."
