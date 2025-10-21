#!/bin/bash

# Load PUID/PGID from config.yml if present
PUID=$(yq e '.researcharr.puid // 1000' /config/config.yml)
PGID=$(yq e '.researcharr.pgid // 1000' /config/config.yml)

# Set ownership of /config and subfolders
chown -R $PUID:$PGID /config

# Set timezone from config.yml
TZ=$(yq e '.researcharr.timezone // "America/New_York"' /config/config.yml)
if [ -n "$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo $TZ > /etc/timezone
  echo "Timezone set to: $TZ"
fi

# Get cron schedule from config.yml
CRON_SCHEDULE=$(yq e '.researcharr.cron_schedule // "0 * * * *"' /config/config.yml)
echo "Using cron schedule: $CRON_SCHEDULE"

# Create cron job file that executes the python script
echo "${CRON_SCHEDULE} python3 /app/app.py" > /etc/cron.d/researcharr-cron
chmod 0644 /etc/cron.d/researcharr-cron
crontab /etc/cron.d/researcharr-cron

# Start cron in the foreground and tail the logs to make them visible with `docker logs`
echo "Starting cron..."
cron -f &
tail -f /config/logs/*.log 2>/dev/null