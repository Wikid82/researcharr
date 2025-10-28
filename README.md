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
  <a href="https://github.com/Wikid82/researcharr/actions/workflows/ci.yml">
    <img src="https://github.com/Wikid82/researcharr/workflows/CI/badge.svg" alt="CI" />
  </a>
  <!-- We run a single CI workflow that builds/tests a Debian-slim based image and runs Trivy scans -->
</p>



## Developer Note: Config Loader & Test Coverage

The `load_config()` function now accepts an optional `path` argument, allowing tests and advanced users to load configuration from any file. This enables robust testing of config edge cases (missing, empty, malformed, or partial configs) and makes it easier to develop and validate new features. The test suite now covers config loading, error handling for connections, database integrity, and logger output.

**Key Features:**
- Modern AJAX web UI (instant navigation, no page reloads)
- Secure login, user management, and error feedback
- Edit all config (including schedule/timezone) from the UI
- Enable/disable and validate up to 5 Radarr & 5 Sonarr instances
- All endpoints and UI behaviors are covered by automated tests

## Developer Note: Linting, typing, and import-shim hardening

We recently enforced the repository linting and typing pipeline locally and in CI: formatters (isort + black), flake8 (E501 now enforced), mypy, and pytest with coverage. During that work we hardened the compatibility import shim used to expose the top-level module as a package so tests and monkeypatching are deterministic across import orders. This resolved an intermittent AttributeError seen in the test suite.

Recommended image tags for reproducing CI or running interactively:

- `local/researcharr:builder` — builds a developer image (matches CI builder stage) and is the recommended tag for reproducing CI validation (mypy + pytest).
- `ghcr.io/wikid82/researcharr:prod` — production runtime image (Debian-slim, built from the multistage `Dockerfile`).
- `ghcr.io/wikid82/researcharr:dev` — developer/debug image (same base as `prod` with extra debugging tools installed).

If you'd like, I can push the verified changes to the `development` branch and monitor CI runs (CI will build the `prod` and `dev` variants and run Trivy); confirm and I'll proceed.

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
- Local docs: see the `docs/` folder in this repository for contributor and user documentation.

API docs / Swagger UI
---------------------

An interactive Swagger UI is available at `/api/v1/docs` and reads the OpenAPI JSON at `/api/v1/openapi.json`.
For security this documentation endpoint requires a valid API key provided via the `X-API-Key` header (it does not allow anonymous or session-only access). Please avoid exposing the docs endpoint to the public internet unless access to the API key is tightly controlled.
- FAQ: see `docs/FAQ.md` for common questions and troubleshooting tips.
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

Runtime image variants (production vs development)

We maintain a single Debian-slim based production image and a debug variant built from the same pipeline. This balances security, compatibility with manylinux wheels, and developer ergonomics.

- `ghcr.io/wikid82/researcharr:prod` — production image based on Debian-slim (recommended for operators). Use this for production deployments; it is built by our CI pipeline from the multistage `Dockerfile`.
- `ghcr.io/wikid82/researcharr:dev` — debug/developer image (same base as `prod` with extra dev tooling installed). Use this when you need a shell or debugging utilities.

Tags published (examples):

- `ghcr.io/wikid82/researcharr:<version>-prod` and `ghcr.io/wikid82/researcharr:prod`
- `ghcr.io/wikid82/researcharr:<version>-dev` and `ghcr.io/wikid82/researcharr:dev`

Default policy

CI builds and validates the `prod` and `dev` variants. We run Trivy scans during CI and require remediation for any CRITICAL/HIGH findings before promoting an image to a production recommendation.

Which to run locally (quick guide)

- Production / operator (recommended): use the `prod` image and mount a persistent `/config` directory on the host (example below).
- Development / debugging: use the `dev` image (it includes a shell and common debugging tools).
Examples

1) Run the recommended production image (distroless):

```bash
mkdir -p /path/to/config /path/to/logs
docker run -d \
  --name researcharr \
  -v /path/to/config:/config \
  -v /path/to/logs:/logs \
  -p 2929:2929 \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:distroless
```

2) Developer quick-run (debug image, with interactive shell):

```bash
# mount and run the debug image (includes shell & dev tools)
docker run --rm -it \
  -v "$(pwd)":/app -w /app \
  -v /path/to/config:/config \
  -p 2929:2929 \
  ghcr.io/wikid82/researcharr:dev /bin/bash
# inside the container you can run tests, linters and the app directly:
python -m pip install -r requirements.txt
python -m pytest tests/
python -u /app/run.py
```

3) Builder-stage testing (matches CI environment):

```bash
# Build the builder image (installs build deps + packages)
docker build --target builder -f Dockerfile.distroless -t local/researcharr:builder .

# Run tests in the builder image (no need to install dev tools locally)
docker run --rm --entrypoint "" -v "$(pwd)":/src -w /src local/researcharr:builder \
  sh -lc "python -m pip install --upgrade pip && pip install mypy pytest && mypy . && pytest tests/"
```

Development config vs user config

- **User / operator config:** mount a persistent host directory at `/config` and let the container populate `config.yml` from `config.example.yml` on first-run. This is the simplest and safest setup for operators.
- **Development config:** when contributing, mount your repo into the container and use the `builder` or `dev` images. Use your host editor to change files and run the in-container test commands. Avoid using the distroless runtime for active development because it lacks a shell and dev tooling.

## Developer compose & debug notes

The repository includes a few compose files and a small helper script to make local development and debugging easier:

- `docker-compose.yml` — production-like compose file for running the container locally with a mounted `./config` directory.
- `docker-compose.dev.yml` — developer convenience compose that mounts the source tree into the container so you can iterate quickly and run tests in-container.
- `docker-compose.hardened.yml` — an optional override demonstrating secure runtime options (for example: `no-new-privileges`, `cap_drop`, running as a non-root user, `tmpfs` for `/tmp`). Use it as an example by combining it with the base compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.hardened.yml up --build
```

Preparing a local config

```bash
cp config.example.yml config/config.yml
```

Run the development compose (mount source, run in foreground):

```bash
docker compose -f docker-compose.dev.yml up --build
```

Debugging and collecting logs

We include `debug-collect.sh` which gathers useful debugging artifacts (container logs, `/app/VERSION`, and the mounted `config` contents) into a tarball. Run it on a host that can reach your containers to collect artifacts quickly.

Example:

```bash
./debug-collect.sh > debug-collect-output.tar.gz
```

CI smoke-test artifacts

If a CI smoke-test fails the workflows will now attach a `smoke-logs-*.tar.gz` artifact containing container logs and a small dump of the health output. This helps debugging flaky startup issues quickly.



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

researcharr exposes a single set of `/health` and `/metrics` endpoints on port `2929` (the combined web UI + scheduler service). Use these endpoints for Docker healthchecks, monitoring, and basic debugging.

- `/health`: Returns a JSON object indicating the health of the service (DB, config, background threads, and current time).
- `/metrics`: Returns a JSON object with basic metrics such as total requests, errors, and queue lengths.

**Docker Compose Healthcheck Example:**

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

You can also check these endpoints manually:

```bash
curl http://localhost:2929/health
curl http://localhost:2929/metrics
```

See `docs/Health-and-Metrics.md` for full details.

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

## Versioning & Releases (summary)

We include build metadata with each image and expose it at runtime for
traceability. For full details (CI tagging, labels, manifest inspection,
and troubleshooting) see `docs/Versioning.md`.

Quick check (run locally):

```bash
curl http://localhost:2929/api/version
```

The detailed policy and examples are in `docs/Versioning.md`.

Notes about CI pre-release behavior:

- If a commit is decorated with an exact tag (for example `v1.2.3`), the CI
  build will use that tag (stripping a leading `v`) as the canonical version
  added to labels and tags.
- For non-tag builds CI will generate a small pre-release version so images
  remain traceable. The format used by CI is `0.0.0-alpha.<run>` by default
  (where `<run>` is the GitHub Actions run number). CI will also create a
  build-specific tag such as `0.0.0-alpha.45-build45` so you can correlate an
  image with a particular workflow run.

All of these values are written into `/app/VERSION` in the image and are
exposed via `GET /api/version`. Use that endpoint (or the image digest from
CI) to confirm exactly which build you are running.

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


