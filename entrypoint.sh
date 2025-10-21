#!/bin/bash

# Default to every hour if not set
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 * * * *"}
echo "Using cron schedule: $CRON_SCHEDULE"

# Create cron job file that executes the python script
echo "${CRON_SCHEDULE} python3 /app/app.py" > /etc/cron.d/researcharr-cron

# Give execution rights on the cron job
chmod 0644 /etc/cron.d/researcharr-cron

# Apply cron job
crontab /etc/cron.d/researcharr-cron

# Start cron in the foreground and tail the logs to make them visible with `docker logs`
echo "Starting cron..."
cron -f &
tail -f /config/logs/*.log