<p align="center" style="background: rgba(255, 255, 255, 1); padding: 16px; border-radius: 8px;">
  <img src="static/logo.jpg" alt="researcharr logo" height="150"/>
</p>

<p align="center"
![Docker Publish (main)](https://github.com/Wikid82/researcharr/actions/workflows/docker-publish.yml/badge.svg?branch=main)
![Docker Publish (development)](https://github.com/Wikid82/researcharr/actions/workflows/docker-publish.yml/badge.svg?branch=development)
</p>

# researcharr

A modern, always-on utility to automatically trigger searches in the *arr suite to keep files up to date with any scoring or custom format changes. Features a secure, AJAX-powered web UI for managing all settings, per-instance validation, and robust automated test coverage.

## Developer Note: Config Loader & Test Coverage

The `load_config()` function now accepts an optional `path` argument, allowing tests and advanced users to load configuration from any file. This enables robust testing of config edge cases (missing, empty, malformed, or partial configs) and makes it easier to develop and validate new features. The test suite now covers config loading, error handling for connections, database integrity, and logger output.

**Key Features:**
- Modern AJAX web UI (instant navigation, no page reloads)
- Secure login, user management, and error feedback
- Edit all config (including schedule/timezone) from the UI
- Enable/disable and validate up to 5 Radarr & 5 Sonarr instances
- All endpoints and UI behaviors are covered by automated tests

## Project Structure

```
researcharr/
├── config.example.yml
├── .github/
│   └── workflows/
│       └── docker-publish.yml
├── Dockerfile
├── LICENSE
├── README.md
├── researcharr.py
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```

Documentation

- Local docs: see the `docs/` folder in this repository for contributor and user documentation.
- Published docs (GitHub Pages): https://wikid82.github.io/researcharr/  (deployed from `docs/` on `main` via GitHub Actions)

![GitHub Pages](https://github.com/Wikid82/researcharr/workflows/Deploy%20docs%20to%20GitHub%20Pages/badge.svg)

Preview docs for other branches

Preview docs for other branches

- Branch previews are available under the Pages site at `/previews/<branch>/` (for example `https://wikid82.github.io/researcharr/previews/development/`). Previews are generated automatically for non-`main` branches on push.

Docs validation

- Pull requests to `development` and `main` run a docs link-checker that validates internal and external links in the `docs/` site; fix any reported link errors before merging.

Docker images per-branch (automated)

- When CI completes successfully for a push, a Docker image is automatically published to GitHub Container Registry and tagged with the branch name. Example tags:
  - `ghcr.io/wikid82/researcharr:plugins`
  - `ghcr.io/wikid82/researcharr:branch-plugins`
- Special branch tags: when the branch is `development` or `main`, the workflow also publishes additional tags (`:development` and `:latest` respectively).

How to pull & run a branch image:

```bash
docker pull ghcr.io/wikid82/researcharr:plugins
docker run --rm -v /path/to/config:/config -p 2929:2929 ghcr.io/wikid82/researcharr:plugins
```

Notes:

- Images are only published after CI passes for push events (not for PRs from forks) to protect secrets and avoid accidental publishes.
- Branch images are useful for QA/testing feature branches. Consider cleaning up unused images periodically.


## Requirements

- Python 3.8+
- Docker (for containerized usage)
- [Radarr](https://radarr.video/) and/or [Sonarr](https://sonarr.tv/) instances

All required Python packages are listed in `requirements.txt` and are installed automatically when building or running the Docker container. This includes:

- Flask (for the web UI)
- Werkzeug (for secure login/password hashing)
- PyYAML (for YAML config and user management)

If running outside Docker, install dependencies with:

```bash
pip install -r requirements.txt
```


## Health & Metrics Endpoints (NEW)

researcharr now provides built-in `/health` and `/metrics` endpoints for both the main app and the web UI. These endpoints are designed for Docker healthchecks, monitoring, and debugging.

- `/health`: Returns a JSON object indicating the health of the service (DB, config, background threads, and current time).
- `/metrics`: Returns a JSON object with basic metrics such as total requests, errors, and (for the app) queue lengths.

**Docker Compose Healthcheck Example:**

For the main app (recommended):

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

For the web UI (optional):

```yaml
services:
  webui:
    # ...other config...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2929/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

You can also check these endpoints manually:

```bash
curl http://localhost:2929/health
curl http://localhost:2929/metrics
```

See the new `Health-and-Metrics.md` wiki page for full details.

## CI and Docker publishing (CI updates)

The project runs continuous integration on every push and every pull request via `.github/workflows/ci.yml` (root and project-level workflows).

CI highlights for contributors:

- Linting: `flake8` (style and simple mistakes).
- Formatting checks: `black` and `isort` are run in check-only mode in CI. `isort` is configured to use Black's import formatting via `researcharr/.isort.cfg`.
- Type checks: `mypy` where configured.
- Tests: `pytest` runs the full test suite.
- Caching: The workflow uses pip caching to speed up dependency installs.

Local developer quick-start:

1. Install dependencies into a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the repo formatting and tests (CI uses check-only for formatting; locally run the auto-fixers before committing):

```bash
isort --profile=black .
black .
python -m pytest tests/
```

3. Use `pre-commit` (recommended) to run checks before committing. See `.pre-commit-config.yaml` in the repository root.

Docker publishing and tags:

Docker images are built and published for branches via `researcharr/.github/workflows/docker-publish.yml`. Images are tagged per-branch and pushed to GitHub Container Registry (GHCR):

- `ghcr.io/wikid82/researcharr:<branch>`
- `ghcr.io/wikid82/researcharr:branch-<branch>`

Special tags are pushed for these branches:

- `main` → `:latest`
- `development` → `:development`

If you prefer not to publish images from forks or pull requests, update the workflow to only push images when the event is a repository `push` and optionally restrict to certain branches.

## How to Use

1.  **Create a configuration directory:**
  ```bash
  mkdir -p /path/to/config
  # You do not need to manually copy config.yml unless you want to pre-configure settings.
  # If /config/config.yml is missing, it will be auto-created from config.example.yml at container startup.
  ```

2.  **Edit your configuration:**
  Open `/path/to/config/config.yml` in your favorite editor and fill in the values for up to 5 Radarr and 5 Sonarr instances, schedule, and timezone. Each instance can be enabled or disabled. All options are documented in the example file. The scheduler expression (cron-like) can also be edited from the "Scheduling" tab in the web UI; the app uses an in-process scheduler (APScheduler) to run the background processing according to that expression.

3.  **Run the container:**
    You can use either Docker Compose (recommended) or a `docker run` command. See the examples below. The first time the script runs, it will create a `researcharr.db` file and a `logs` directory inside your config volume.


4.  **Check the logs and health:**
  - Live logs are streamed and can be viewed using the `docker logs` command. See the Logging section for more details.
  - Health and metrics endpoints are available for monitoring and Docker healthchecks (see above).

  ## Environment variables

  See `docs/Environment-Variables.md` for the full list of runtime environment variables (PUID, PGID, TIMEZONE, LOGLEVEL, WEBUI_PORT, WEBUI_RESET_TOKEN) and examples for Docker Compose. These variables must be set before container start; the web UI no longer allows editing PUID/PGID/Timezone.

  ## Production deployment (recommended)

  For production use, run the web UI under a WSGI server such as Gunicorn instead of the Flask development server. Example:

  ```bash
  # Run with 3 workers and thread-based workers; tune GUNICORN_WORKERS/GUNICORN_THREADS
  gunicorn -w ${GUNICORN_WORKERS:-3} -k gthread --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-30} \
    researcharr.factory:app
  ```

  Set `GUNICORN_WORKERS`, `GUNICORN_THREADS`, and `GUNICORN_TIMEOUT` via environment variables in your production deployment to tune concurrency and timeouts.

5.  **Use the Web UI (AJAX-powered, always-on):**
    - Launch with:
      ```bash
      docker exec -it researcharr python3 /app/webui.py
      ```
      Then visit [http://localhost:2929](http://localhost:2929) in your browser.
    - **Login is required.**
      - Default username: `researcharr` on first-run
      - Default password: a secure random password is generated automatically on first startup and its plaintext value is logged once to the application logs. The generated password is stored as a hashed value in `config/webui_user.yml`.
      - Troubleshooting / retrieving the initial password:

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
- You can set your timezone and the scheduler expression (cron-like) from the Scheduling tab in the web UI; changes are saved to config and applied by the in-process scheduler (APScheduler) that runs inside the container. See the wiki page [Scheduling and Timezone](wiki/Scheduling-and-Timezone.md) for details.
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

- Health and metrics endpoints are now available for both the app and web UI. Use them for Docker healthchecks, monitoring, and debugging.
- Log level can be changed live from the web UI General Settings page.

- The container and web UI will always stay up, even if no valid Radarr/Sonarr config is present. You can fix your configuration at any time using the web UI.
- Each Radarr and Sonarr instance in the web UI now has a "Validate & Save" button. This tests the connection and performs a dry run for that instance, showing the result instantly.
- Radarr and Sonarr URLs must start with `http://` or `https://` and have a valid API key. If not, the instance will be skipped and a warning will be shown in the UI and logs.


