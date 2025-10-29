#!/bin/bash

set -euo pipefail

# Entrypoint: honor PUID/PGID (env or config.yml), chown mounted dirs,
# then drop privileges and exec the application as the target UID/GID.

# Ensure /config exists
mkdir -p /config

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

# Apply ownership so that the runtime UID/GID can write to bind mounts.
# Ignore failures (in case files are missing) to keep start robust.
chown -R ${PUID}:${PGID} /config || true
chown -R ${PUID}:${PGID} /app || true

mkdir -p /config/logs
touch /config/researcharr.db >/dev/null 2>&1 || true

# Set timezone if available
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo "$TZ" > /etc/timezone
  echo "Timezone set to: $TZ"
fi

echo "Starting researcharr (web UI + scheduler) as UID=${PUID} GID=${PGID}..."

# Export PUID/PGID for the Python helper
export PUID PGID

# Drop privileges and exec the Python app. We use a tiny Python helper
# so we don't need gosu or su-exec in the image.
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
os.execv('/usr/bin/python3', ['/usr/bin/python3', '/app/run.py'])
PY
#!/bin/bash

## Ensure /config directory exists and is writable and that a config file
## exists before attempting to read values from it with yq. This avoids
## yq errors during first-run container start when /config is empty.
if [ ! -d /config ]; then
  mkdir -p /config
fi
if [ ! -w /config ]; then
  echo "ERROR: /config directory is not writable. Check your Docker volume mount and permissions."
  exit 1
fi

## Ensure a config.yml is present (copy from bundled example on first run)
if [ ! -f /config/config.yml ]; then
  if [ -f /app/config.example.yml ]; then
    cp /app/config.example.yml /config/config.yml
    if [ $? -eq 0 ]; then
      echo "Copied default config.example.yml to /config/config.yml."
    else
      echo "ERROR: Failed to copy config.example.yml to /config/config.yml. Check permissions."
      exit 1
    fi
  else
    echo "No config.yml or config.example.yml found!"
    exit 1
  fi
fi

## Read PUID/PGID and timezone from the now-present config file. Use
## sensible defaults if the values are missing. We parse YAML with Python
## so we don't need to install an extra dependency (yq) in the image.
if [ -f /config/config.yml ]; then
  # Run the small Python snippet and read its stdout into the three variables.
  # Previously the Python source was fed directly into `read`, which caused
  # shell variables like PUID to contain the literal Python code (e.g.
  # "import yaml,sys") and made `chown` fail with an invalid user error.
  read -r PUID PGID TZ < <(python3 - <<'PY'
import yaml,sys
try:
    cfg = yaml.safe_load(open('/config/config.yml')) or {}
except Exception:
    cfg = {}
rs = cfg.get('researcharr', {})
print(rs.get('puid',''))
print(rs.get('pgid',''))
#!/bin/bash

set -euo pipefail

# Ensure /config directory exists. The entrypoint runs as root so we can
# create and set permissions for bind-mounted directories before dropping
# privileges to the unprivileged runtime user.
if [ ! -d /config ]; then
  mkdir -p /config
fi

# Prefer environment variables PUID/PGID when provided (docker-compose
# or the user may set these). If not provided, try to read them from
# /config/config.yml; default to 1000 when missing.
PUID_ENV=${PUID:-}
PGID_ENV=${PGID:-}

PUID=""
PGID=""
TZ=""

if [ -n "${PUID_ENV}" ] && [ -n "${PGID_ENV}" ]; then
  PUID=${PUID_ENV}
  PGID=${PGID_ENV}
else
  if [ -f /config/config.yml ]; then
    # Read numeric puid/pgid and timezone if present
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

# Apply ownership to /config and /app so the runtime user can write as expected.
# Use chown -R but ignore failures for missing files.
chown -R ${PUID}:${PGID} /config || true
chown -R ${PUID}:${PGID} /app || true

# Create logs and db files
mkdir -p /config/logs
touch /config/researcharr.db || true

# Set timezone if available
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo "$TZ" > /etc/timezone
  echo "Timezone set to: $TZ"
fi

echo "Starting researcharr (web UI + scheduler) as UID=${PUID} GID=${PGID}..."

# Drop privileges using a tiny Python helper which sets gid/uid and then
# execs the target process. This avoids adding gosu/su-exec to the image.
python3 - <<PY
import os, sys
try:
    uid = int(os.environ.get('PUID', '%s'))
    gid = int(os.environ.get('PGID', '%s'))
except Exception:
    uid = %s
    gid = %s

# setgid before setuid
try:
    os.setgid(gid)
except Exception as e:
    print('Warning: failed to setgid', e, file=sys.stderr)
try:
    os.setuid(uid)
except Exception as e:
    print('Warning: failed to setuid', e, file=sys.stderr)

os.execv('/usr/bin/python3', ['/usr/bin/python3', '/app/run.py'])
PY