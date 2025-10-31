# Health and Metrics Endpoints

## Overview

researcharr exposes built-in health and metrics endpoints on port `2929` (the combined web UI + scheduler service). These endpoints are designed for use with Docker healthchecks, monitoring tools, and debugging.

## Endpoints

- `/health` — Returns a JSON object indicating the health of the service (DB, config, background threads, and current time).
- `/metrics` — Returns a JSON object with basic metrics such as total requests, errors, and (for the app) queue lengths.

## How to Use

### Docker Compose Healthcheck Example

Configure the single `researcharr` service to use the `/health` endpoint on port `2929`:

```yaml
services:
  researcharr:
    # ...other config...
    command: python researcharr.py serve
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2929/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Manual Check

You can also check the endpoints manually (web UI runs on port 2929 by default):

```bash
curl http://localhost:2929/health
curl http://localhost:2929/metrics
```

## Live Log Level Control

- The log level for both the app and web UI can now be set from the General Settings page in the web UI.
- Changes to the log level are applied live (no restart required).
- This allows you to increase verbosity for debugging or reduce log volume in production.

## Metrics Details

- `requests_total`: Number of HTTP requests handled
- `errors_total`: Number of errors encountered
- `last_health_check`: Timestamp of the last health check
- `radarr_queue_length`, `sonarr_queue_length` (app only): Current queue lengths

## Why Use These Endpoints?

- **Docker healthchecks**: Ensures your container is restarted if the app becomes unresponsive.
- **Monitoring**: Integrate with Prometheus, Grafana, or other tools for visibility.
- **Debugging**: Quickly check if the app is running and healthy.

---

For more details, see the main README and Configuration docs.
