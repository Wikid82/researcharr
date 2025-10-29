<p align="center" style="background: rgba(255, 255, 255, 1); padding: 16px; border-radius: 8px;">
  <img src="static/logo.jpg" alt="researcharr logo" height="150"/>
</p>


# researcharr

A modern, always-on utility to automatically trigger searches in the *arr suite to keep files up to date with any scoring or custom format changes. Features a secure, AJAX-powered web UI for managing all settings, per-instance validation, and robust automated test coverage.

# status
 
<p align="center">
  <a href="https://codecov.io/gh/Wikid82/researcharr">
    <img src="https://codecov.io/gh/Wikid82/researcharr/graph/badge.svg?token=LBEJBSUPLX" alt="Codecov" />
  </a>
  <p align="center" style="background: rgba(255, 255, 255, 1); padding: 16px; border-radius: 8px;">
    <img src="static/logo.jpg" alt="researcharr logo" height="120"/>
  </p>

  # researcharr

  A compact, operator-friendly service to validate and trigger “arr” searches (Radarr/Sonarr/etc.) via a secure web UI and scheduler. Designed for reliable automation, observability, and easy Docker deployment.

  Badges

  [![CI](https://github.com/Wikid82/researcharr/workflows/CI/badge.svg)](https://github.com/Wikid82/researcharr/actions/workflows/ci.yml) [![Docs](https://github.com/Wikid82/researcharr/workflows/Deploy%20docs%20to%20GitHub%20Pages/badge.svg)](https://wikid82.github.io/researcharr/)

  Quick start

  1) Create a config directory and run the production image (recommended):

  ```bash
  mkdir -p /path/to/config
  docker run -d \
    --name researcharr \
    -v /path/to/config:/config \
    -p 2929:2929 \
    --restart unless-stopped \
    ghcr.io/wikid82/researcharr:prod
  ```

  2) Visit the web UI at: http://localhost:2929/

  3) Want to develop or run the tests? Use the builder/dev images or the `docker-compose.dev.yml` from the repo. See docs for details.

  Why use researcharr?

  - Small, focused: validates and schedules searches against Radarr/Sonarr-like services.
  - Docker-first: production and dev images (CI-validated) with a consistent multistage build.
  - Observability: /health and /metrics endpoints, logs, and CI-backed tests and scans.

  More details

  This repository includes full docs with configuration, environment variables, CI notes, and operator guidance. Please see the site for full instructions and advanced topics:

  - Getting started & quick reference: `docs/Getting-Started.md`
  - Runtime env vars: `docs/Environment-Variables.md`
  - Health, metrics and logging: `docs/Health-and-Metrics.md` and `docs/Logs.md`
  - Contributing and development workflow: `docs/CI-and-Development.md` and `docs/Contributing.md`

  Contributors

  See `docs/Contributing.md` for guidance on development, tests, and the contributor workflow.

  License

  This project is released under the terms of the MIT license. See `LICENSE` for details.

  If you'd like, I can open a PR merging the `reception` branch into `development` once you confirm — I left longer operator/developer guidance in `docs/` and trimmed this `README.md` to a short quickstart and links to the full documentation.
        If you start the full web UI (not a one-shot scheduler run) the first-run password will be logged once to container logs. To retrieve it:

        ```bash
        # If running detached:
        docker logs --tail 200 researcharr | grep -i "Generated web UI initial password" -A1 -B1

        # If you prefer to persist the config directory to inspect files locally:
        mkdir -p ./config
        docker run --rm -v "$(pwd)/config:/config" researcharr:local python3 /app/run.py &
        # then check the generated file locally after startup:
        cat ./config/webui_user.yml
        ```

        Note: the plaintext password is only logged once for operator convenience; only the hash is persisted in `webui_user.yml`.
      - To change credentials after first-run, use the "User Settings" tab in the web UI (this updates `webui_user.yml`).
      - If you need to allow unauthenticated password resets, set the environment variable `WEBUI_RESET_TOKEN` to a secret value and use the web UI "Forgot password?" link to reset credentials using that token. Without `WEBUI_RESET_TOKEN` the reset page is disabled.
    - **AJAX navigation:** Sidebar and header never reload; only the main content area updates. All forms and navigation are AJAX-powered for instant feedback.
    - **Per-instance validation:** Each Radarr and Sonarr instance has a "Validate & Save" button for instant connection testing and dry-run, with results shown in the UI.
    - **Error feedback:** All error messages (e.g., invalid config, missing API key) are shown instantly in the UI.
    - **Multi-instance:** Enable/disable and configure up to 5 Radarr and 5 Sonarr instances. All instance settings are collapsed by default; enable to expand and edit.
    - **Always-on:** The container and web UI never exit on invalid config—fix your settings at any time using the web UI.
    - **User credentials:** Managed in `webui_user.yml` and editable from the UI.
    - **Test coverage:** All endpoints and UI behaviors are covered by automated tests.

## Configuration (All Editable in Web UI)

All configuration is now managed in a single YAML file: `/path/to/config/config.yml`.

- See `config.example.yml` for a fully documented template.
  - You can set your timezone and the scheduler expression (cron-like) from the Scheduling tab in the web UI; changes are saved to config and applied by the in-process scheduler (APScheduler) that runs inside the container. See `docs/Getting-Started.md` for scheduling details and examples.
- Example URLs for Docker default network: `http://radarr:7878` and `http://sonarr:8989`.

## State Management

This application uses a **SQLite database** (`researcharr.db`) to manage a persistent queue of items to process. This ensures that every eligible media file is eventually searched for without repetition.

*   **Workflow:**
    1.  On the first run, or any time the processing queue is empty, the script scans your entire library to find all items that need an upgrade and populates the queue. This can take some time depending on the size of your library.
    2.  On all subsequent runs, the script simply takes the next batch of items from the queue, triggers a search, and removes them from the queue. These runs are very fast.
*   **Persistence:** The database file is stored in your main config volume (`/path/to/config/researcharr.db`), so the queue is maintained even if you restart or update the container.


## Logging & Live Log Level Control (NEW)

The log level for both the app and web UI can now be set from the General Settings page in the web UI. Changes are applied live (no restart required). This allows you to increase verbosity for debugging or reduce log volume in production.

The application creates three separate log files inside a `logs` directory within your main config volume (`/path/to/config/logs/`):

*   `researcharr.log`: Contains general application status, such as starting and finishing a run.
*   `radarr.log`: Contains all logs specifically related to Radarr API calls and processing.
*   `sonarr.log`: Contains all logs specifically related to Sonarr API calls and processing.

You can view a combined, real-time stream of all logs by running:
```bash
docker logs -f researcharr
```

---


docker exec -it researcharr python3 /app/webui.py

## Web UI (AJAX Navigation, Always-On)

**Key Features:**
- **AJAX Navigation:** Sidebar and header never reload; only the main content area updates. All forms and navigation are AJAX-powered for instant feedback.
- **Per-Instance Validation:** Each Radarr and Sonarr instance has a "Validate & Save" button for instant connection testing and dry-run, with results shown in the UI.
- **Error Feedback:** All error messages (e.g., invalid config, missing API key) are shown instantly in the UI.
- **Multi-Instance:** Enable/disable and configure up to 5 Radarr and 5 Sonarr instances. All instance settings are collapsed by default; enable to expand and edit.
- **Always-On:** The container and web UI never exit on invalid config—fix your settings at any time using the web UI.
- **User Credentials:** Managed in `webui_user.yml` and editable from the UI.
- **Test Coverage:** All endpoints and UI behaviors are covered by automated tests.
- **Responsive:** The UI is optimized for both desktop and mobile browsers.

To use the web UI, run:
```bash
docker exec -it researcharr python3 /app/webui.py
```
and visit [http://localhost:2929](http://localhost:2929).

**Dependencies:** Flask, Werkzeug, and PyYAML are required for the web UI and are installed automatically in Docker. If running locally, install them with `pip install -r requirements.txt`.

**User credentials:** Managed in `webui_user.yml` and editable from the "User Settings" tab in the web UI.

### Download Queue Limit & Reprocessing Interval (per instance)

Each Radarr and Sonarr instance now supports:

- `max_download_queue` (default: 15): If the number of items in the instance's download queue is at or above this value, researcharr will skip upgrades for that instance until the next run. This helps prevent overloading your download client.
- `reprocess_interval_days` (default: 7): Items will be reprocessed (searched again) after this many days, even if they were previously processed. This helps ensure upgrades are retried over time. You can edit this value for each instance in the web UI or directly in `config.yml`.

```bash
docker run -d \
  --name=researcharr \
  -v /path/to/config:/config \
  -p 2929:2929 \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:latest
```
**Note:** All configuration is handled in `/path/to/config/config.yml`. If this file is missing, it will be auto-created from `config.example.yml` at container startup. No environment variables or `.env` file are required.


  ## Important Notes

  - The service exposes `/health` and `/metrics` on port `2929`. Use them for Docker healthchecks, monitoring, and debugging.
- Log level can be changed live from the web UI General Settings page.

- The container and web UI will always stay up, even if no valid Radarr/Sonarr config is present. You can fix your configuration at any time using the web UI.
- Each Radarr and Sonarr instance in the web UI now has a "Validate & Save" button. This tests the connection and performs a dry run for that instance, showing the result instantly.
- Radarr and Sonarr URLs must start with `http://` or `https://` and have a valid API key. If not, the instance will be skipped and a warning will be shown in the UI and logs.

Deployment & resource guidance

See `docs/Deployment-and-Resources.md` for examples and recommendations on
how to run researcharr with Docker, Docker Compose, or Kubernetes and how
to use the `JOB_TIMEOUT`, `JOB_RLIMIT_AS_MB`, `JOB_RLIMIT_CPU_SECONDS`,
and `RUN_JOB_CONCURRENCY` environment variables to control job runtime
and resource usage.


