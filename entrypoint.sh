#!/bin/bash

# Load PUID/PGID from config.yml if present
# Ensure /config directory exists and is writable
if [ ! -d /config ]; then
  mkdir -p /config
fi
if [ ! -w /config ]; then
  echo "ERROR: /config directory is not writable. Check your Docker volume mount and permissions."
  exit 1
fi
PUID=$(yq '.researcharr.puid' /config/config.yml)
PUID=${PUID:-1000}
PGID=$(yq '.researcharr.pgid' /config/config.yml)
PGID=${PGID:-1000}

# Set ownership of /config and subfolders
chown -R $PUID:$PGID /config

# Set timezone from config.yml
TZ=$(yq '.researcharr.timezone' /config/config.yml)
TZ=${TZ:-America/New_York}
if [ -n "$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo $TZ > /etc/timezone
  echo "Timezone set to: $TZ"
fi




# Ensure /config/config.yml exists, copy from example if missing
if [ ! -f /config/config.yml ]; then
  if [ -f /app/config.example.yml ]; then
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
mkdir -p /config/logs

# Ensure /config/researcharr.db exists (touch will not overwrite if present)
touch /config/researcharr.db

# Start the web UI in the background
echo "Starting researcharr web UI on port 2929..."
python3 /app/webui.py &

# Run the script once at startup
echo "Running researcharr at startup..."
python3 /app/app.py

# Get cron schedule from config.yml (settable in the web UI Scheduling tab)
CRON_SCHEDULE=$(yq '.researcharr.cron_schedule' /config/config.yml)
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 * * * *"}
echo "Using cron schedule: $CRON_SCHEDULE"

# Validate cron schedule (basic check: must have 5 fields)
CRON_FIELD_COUNT=$(echo "$CRON_SCHEDULE" | awk '{print NF}')
if [ "$CRON_FIELD_COUNT" -ne 5 ]; then
  echo "Warning: Invalid cron schedule '$CRON_SCHEDULE'. Falling back to '0 * * * *' (hourly)."
  CRON_SCHEDULE="0 * * * *"
fi

# Create cron job file that executes the python script
echo "${CRON_SCHEDULE} python3 /app/app.py" > /etc/cron.d/researcharr-cron
chmod 0644 /etc/cron.d/researcharr-cron
crontab /etc/cron.d/researcharr-cron

# Start cron in the foreground and tail the logs to make them visible with `docker logs`
echo "Starting cron..."
cron -f &
tail -f /config/logs/*.log 2>/dev/null