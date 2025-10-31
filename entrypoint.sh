#!/bin/bash

set -euo pipefail

# Entrypoint: ensure necessary directories exist, honor PUID/PGID (env or
# config.yml), attempt to chown mounted dirs (with fallbacks), then drop
# privileges and exec the application as the target UID/GID.

# Ensure /config and /app exist so subsequent operations don't fail on empty mounts
mkdir -p /config
mkdir -p /app

# Prefer environment variables when provided
PUID_ENV="${PUID:-}"
PGID_ENV="${PGID:-}"

PUID=""
PGID=""
TZ=""

if [ -n "$PUID_ENV" ] && [ -n "$PGID_ENV" ]; then
  PUID="$PUID_ENV"
  PGID="$PGID_ENV"
else
  # If config.yml exists, try to parse puid/pgid/timezone from it
  if [ -f /config/config.yml ]; then
    read -r PUID PGID TZ < <(python3 - <<'PY'
import yaml
try:
    cfg = yaml.safe_load(open('/config/config.yml')) or {}
except Exception:
    cfg = {}
rs = cfg.get('researcharr', {})
print(rs.get('puid',''))
print(rs.get('pgid',''))
print(rs.get('timezone',''))
PY
)
  fi
fi

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Config PUID=${PUID} PGID=${PGID}"

# Create expected runtime files/dirs before attempting ownership changes
mkdir -p /config/logs
touch /config/researcharr.db >/dev/null 2>&1 || true

# Attempt to set ownership so that the runtime UID/GID can write to bind mounts.
# Some mount types (NFS with root_squash, CIFS, FUSE) or rootless Docker setups
# may prevent chown. Detect whether chown is possible and only warn once if
# it isn't; otherwise fall back to a permissive chmod so the container can
# continue. If the container is not running as root, skip chown attempts
# (they will fail) and use chmod where helpful.
_try_chown_or_chmod() {
  local target="$1"
  # If not running as root, skip chown attempts (they will fail) and do a
  # permissive chmod so the runtime user can still write where possible.
  if [ "$(id -u)" -ne 0 ]; then
    echo "Note: not running as root; skipping chown for ${target} and applying permissive chmod if possible."
    chmod -R a+rwX "${target}" 2>/dev/null || true
    return
  fi

  if chown -R "${PUID}":"${PGID}" "${target}" 2>/dev/null; then
    echo "chown ${target} -> ${PUID}:${PGID}"
  else
    # Only emit a single, clear warning to avoid log spam; apply chmod fallback
    # so the container can proceed even when the filesystem disallows chown.
    echo "Warning: chown ${target} failed (operation not permitted). Applying permissive chmod fallback and continuing..." >&2
    chmod -R a+rwX "${target}" 2>/dev/null || true
  fi
}

_try_chown_or_chmod /config

# If /app is a host mount and is empty, populate it from the baked-in copy
# so development containers that mount an empty directory still have the
# repository files available. This runs as root before we drop privileges.
if [ -d /opt/researcharr_baked ] && [ -z "$(ls -A /app 2>/dev/null)" ]; then
  echo "Populating /app from baked image copy at /opt/researcharr_baked"
  cp -a /opt/researcharr_baked/. /app || true
fi

_try_chown_or_chmod /app

# Set timezone if available and writable
TZ=${TZ:-America/New_York}
# Try to set system timezone by symlinking /etc/localtime. If the container
# filesystem disallows modifying /etc (common on read-only images or when
# running non-root), fall back to exporting TZ for the process and record
# the desired timezone under /config so the app can read it if needed.
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  if ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime 2>/dev/null; then
    echo "$TZ" > /etc/timezone || true
    echo "Timezone set to: $TZ"
  else
    # Don't treat this as a hard failure. Export TZ so Python/cron libs
    # honor the configured timezone, and persist it under /config so the
    # application can also read it from disk.
    export TZ="$TZ"
    if mkdir -p /config 2>/dev/null; then
      echo "$TZ" > /config/timezone || true
    fi
    echo "Notice: could not write /etc/localtime; exported TZ and saved /config/timezone (TZ=${TZ})." >&2
  fi
fi

echo "Starting researcharr (web UI + scheduler) as UID=${PUID} GID=${PGID}..."

# Export PUID/PGID for the Python helper
export PUID PGID

# Capture any command/args passed to the entrypoint so the Python helper
# can exec the user-supplied command after dropping privileges. Docker
# appends the container CMD as arguments to the entrypoint; preserve the
# passed arguments reliably (works for array-form or string commands).
# Use "$*" to join positional parameters into a single string, and
# ensure the env var is present (empty when no CMD was provided).
if [ "$#" -gt 0 ]; then
  ENTRYPOINT_CMD="$*"
else
  ENTRYPOINT_CMD=""
fi
export ENTRYPOINT_CMD

# Debug: show the resolved command (this line can be removed once debugging is complete)
# (debug echo removed)

# Drop privileges using a tiny Python helper which sets gid/uid and then
# execs the target process. This avoids adding gosu/su-exec to the image.
# Allow bypassing the privilege-drop helper for debugging or constrained
# environments by setting BYPASS_DROP=1. In that case exec the CMD string
# directly (this keeps behavior identical to running the shell command in
# the container). This is a safe opt-in and useful for debugging only.
if [ "${BYPASS_DROP:-0}" = "1" ]; then
  if [ -n "${ENTRYPOINT_CMD}" ]; then
    exec /bin/sh -c "${ENTRYPOINT_CMD}"
  else
    exec /bin/sh -c "python -u /app/researcharr.py serve"
  fi
fi

python3 - <<'PY'
import os, sys

def to_int(v, default):
    try:
        return int(v)
    except Exception:
        return default

uid = to_int(os.environ.get('PUID'), 1000)
gid = to_int(os.environ.get('PGID'), 1000)

# setgid before setuid
try:
    os.setgid(gid)
except Exception as e:
    print('Warning: setgid failed:', e, file=sys.stderr)
try:
    os.setuid(uid)
except Exception as e:
    print('Warning: setuid failed:', e, file=sys.stderr)

# If the entrypoint was given an explicit command (Docker CMD), exec that
# command after dropping privileges so the container runs what the user
# or compose file requested. Otherwise, fall back to the repository's
# default runtime script at /app/scripts/run.py.
cmd = os.environ.get('ENTRYPOINT_CMD')
if cmd:
    # Use a shell so the CMD string semantics (pipes, &&, etc.) still work
    os.execv('/bin/sh', ['/bin/sh', '-c', cmd])
else:
    # Default behavior: run the repository's scripted entrypoint
    os.execv(sys.executable, [sys.executable, '/app/scripts/run.py'])
PY
