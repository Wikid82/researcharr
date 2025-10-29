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
# may prevent chown — handle failures gracefully and attempt a permissive chmod
# fallback so the container can proceed.
if chown -R ${PUID}:${PGID} /config 2>/dev/null; then
  echo "chown /config -> ${PUID}:${PGID}"
else
  echo "Warning: chown /config failed (operation not permitted). Attempting chmod fallback..."
  chmod -R a+rwX /config 2>/dev/null || true
fi

if chown -R ${PUID}:${PGID} /app 2>/dev/null; then
  echo "chown /app -> ${PUID}:${PGID}"
else
  echo "Warning: chown /app failed (operation not permitted). Attempting chmod fallback..."
  chmod -R a+rwX /app 2>/dev/null || true
fi

# Set timezone if available and writable
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  if ln -snf /usr/share/zoneinfo/$TZ /etc/localtime 2>/dev/null; then
    echo "$TZ" > /etc/timezone || true
    echo "Timezone set to: $TZ"
  else
    echo "Warning: failed to set /etc/localtime (permission denied). Timezone not set inside container." >&2
  fi
fi

echo "Starting researcharr (web UI + scheduler) as UID=${PUID} GID=${PGID}..."

# Export PUID/PGID for the Python helper
export PUID PGID

# Drop privileges using a tiny Python helper which sets gid/uid and then
# execs the target process. This avoids adding gosu/su-exec to the image.
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

# Exec the application so it becomes PID 1
os.execv(sys.executable, [sys.executable, '/app/run.py'])
PY