# Environment variables

This document lists runtime environment variables used by researcharr. Set these in your Docker Compose, systemd unit, or container run command before starting the service.

## Required / important

- PUID
  - Default: `1000`
  - Description: The UID to use for files created by the process when writing into mounted volumes. Must be an integer. If invalid, the app will fall back to `1000` and log a warning.

- PGID
  - Default: `1000`
  - Description: The GID to use for files created by the process when writing into mounted volumes. Must be an integer. If invalid, the app will fall back to `1000` and log a warning.

- TIMEZONE
  - Default: `UTC`
  - Description: Timezone used for scheduling and display. Example: `Europe/London` or `America/Los_Angeles`.

## Optional / runtime

- LOGLEVEL
  - Default: `INFO`
  - Description: Controls the default log level for the web UI and background scheduler. Can still be adjusted at runtime through the General Settings page.

- WEBUI_PORT
  - Default: `2929`
  - Description: TCP port the web UI binds to inside the container. Use `-p HOST:2929` in your `docker run` or configure a matching port mapping in Docker Compose.

- WEBUI_RESET_TOKEN
  - Default: not set
  - Description: If set, enables the unauthenticated reset-password web form. The reset form must include this token to perform password resets via the UI.

- SECRET_KEY
  - Default: not set (required in production)
  - Description: Cryptographic secret used by Flask to sign sessions and other secrets. Must be a long, random value in production. The application will refuse to start in production mode if this is not set.

- SESSION_COOKIE_SECURE
  - Default: `true`
  - Description: If `true`, the session cookie will only be sent over HTTPS. Set to `false` only for local development without TLS.

- SESSION_COOKIE_HTTPONLY
  - Default: `true`
  - Description: If `true`, the session cookie will not be accessible to JavaScript.

- SESSION_COOKIE_SAMESITE
  - Default: `Lax`
  - Description: Controls SameSite attribute of the session cookie. Typical values: `Lax`, `Strict`, `None`.

## Production server / performance (recommended env vars)

- WEB_CONCURRENCY / GUNICORN_WORKERS
  - Default: not set (choose based on CPU)
  - Description: Number of Gunicorn worker processes to run.

- GUNICORN_THREADS
  - Default: not set
  - Description: Number of threads per Gunicorn worker when using the gthread worker class.

- GUNICORN_TIMEOUT
  - Default: 30
  - Description: Request timeout for Gunicorn workers in seconds.

## Notes & best practices

- Do not manage PUID/PGID via the web UI; they are intentionally sourced from environment variables so ownership is deterministic for mounted volumes.
- When running under Docker, set `PUID` and `PGID` to match the user on the host that owns the mounted path to avoid permission issues:

```yaml
services:
  researcharr:
    environment:
      - PUID=1001
      - PGID=1001
      - TIMEZONE=Europe/London
      - LOGLEVEL=INFO
      - WEBUI_PORT=2929
```

- After changing any environment variable, restart the container for changes to take effect.

## CI-related variables (for contributors)

- CODECOV_TOKEN — used by GitHub Actions to upload coverage to Codecov. Not required at runtime in containers.

If you want a machine-readable copy of this list (JSON/YAML), ask and I will add one for automation or tests.
