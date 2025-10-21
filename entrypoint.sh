#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f /config/.env ]; then
  set -a # automatically export all variables
  source /config/.env
  set +a # stop automatically exporting
fi

# Default to every hour if not set
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 * * * *"}
echo "Using cron schedule: $CRON_SCHEDULE"

# Set timezone if TZ variable is set
if [ -n "$TZ" ]; then
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
  echo $TZ > /etc/timezone
  echo "Timezone set to: $TZ"
fi

# Create cron job file that executes the python script
echo "${CRON_SCHEDULE} python3 /app/app.py" > /etc/cron.d/researcharr-cron

# Give execution rights on the cron job
chmod 0644 /etc/cron.d/researcharr-cron

# Apply cron job
crontab /etc/cron.d/researcharr-cron

# Start cron in the foreground and tail the logs to make them visible with `docker logs`
echo "Starting cron..."
cron -f &
tail -f /config/logs/*.log 2>/dev/null