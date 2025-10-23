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
## sensible defaults if the values are missing or yq fails to return
## something parseable.
PUID=$(yq '.researcharr.puid' /config/config.yml 2>/dev/null)
PUID=${PUID:-1000}
PGID=$(yq '.researcharr.pgid' /config/config.yml 2>/dev/null)
PGID=${PGID:-1000}

## Set ownership of /config and subfolders
chown -R $PUID:$PGID /config

## Set timezone from config.yml
TZ=$(yq '.researcharr.timezone' /config/config.yml 2>/dev/null)
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo $TZ > /etc/timezone
  echo "Timezone set to: $TZ"
fi





mkdir -p /config/logs

# Ensure /config/researcharr.db exists (touch will not overwrite if present)
touch /config/researcharr.db

# Start the application (Flask + in-process scheduler) in the foreground.
# We exec here so the Python process becomes PID 1 and receives signals
# directly from Docker.
echo "Starting researcharr (web UI + scheduler)..."
exec python3 /app/run.py