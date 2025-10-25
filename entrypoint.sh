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
  read -r PUID PGID TZ <<'PY'
import yaml,sys
try:
    cfg = yaml.safe_load(open('/config/config.yml')) or {}
except Exception:
    cfg = {}
rs = cfg.get('researcharr', {})
print(rs.get('puid',''))
print(rs.get('pgid',''))
print(rs.get('timezone',''))
PY
  PUID=${PUID:-1000}
  PGID=${PGID:-1000}
else
  PUID=1000
  PGID=1000
  TZ=""
fi

## Set ownership of /config and subfolders
chown -R $PUID:$PGID /config

## Set timezone from parsed value (if available). Only set it when the
## zoneinfo file exists inside the image. If tzdata is not installed the
## path may be absent; we handle that gracefully.
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo "$TZ" > /etc/timezone
  echo "Timezone set to: $TZ"
else
  echo "Timezone $TZ not available in image; leaving system timezone unchanged"
fi





mkdir -p /config/logs

# Ensure /config/researcharr.db exists (touch will not overwrite if present)
touch /config/researcharr.db

# Start the application (Flask + in-process scheduler) in the foreground.
# We exec here so the Python process becomes PID 1 and receives signals
# directly from Docker.
echo "Starting researcharr (web UI + scheduler)..."
exec python3 /app/run.py