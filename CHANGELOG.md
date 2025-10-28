# Changelog

## 2025-10-25

### Packaging & CI

- Added a `Dockerfile.distroless` multi-stage build that produces a minimal distroless runtime image. The final image copies runtime packages from the builder stage into `/install` and sets `PYTHONPATH` so the distroless Python interpreter can import dependencies.
- Added `.github/workflows/distroless-ci.yml` to validate the distroless build in CI: it builds the builder stage, runs mypy + pytest inside that builder, builds the final distroless image, runs Trivy, uploads the JSON artifact, and publishes the distroless image on successful trusted refs.
- Continued support for `Dockerfile.alpine` and the `alpine-ci` workflow for developer-friendly and alternate-variant validation.

### Notes

- We recommend adopting the distroless image for production after CI validation; the repo now publishes both `-distroless` and `-alpine` variants and validates both in CI.

## 2025-10-26

### Developer / CI

- Enforced the developer pipeline (isort + black → flake8 → mypy → pytest + coverage) in CI and locally. Project `.flake8` now excludes virtualenv directories and enforces E501 so line-length violations are surfaced and fixed.
- Hardened the compatibility import shim used by the `researcharr` package so the real implementation module is deterministically loaded and registered in `sys.modules`. This fixes intermittent test failures caused by import/monkeypatch ordering.
- Updated docs/README guidance with recommended debug image tags: `local/researcharr:builder` (CI-like builder), `local/researcharr:alpine` (interactive debugging), and `ghcr.io/wikid82/researcharr:distroless` (production).

### Security

- Secured the interactive API documentation (Swagger UI) at `/api/v1/docs` so it requires a valid API key in the `X-API-Key` header. The docs no longer allow anonymous or session-only access to avoid accidental exposure of interactive API call functionality.

### Plugins (alpha)

- Added a large set of example integrations (alpha/test harnesses) under `plugins/` grouped by category:
  - `media/`: Radarr, Sonarr, Lidarr, Readarr, Whisparr, Headphones, Sick Beard, SickRage, Mylar3, Bobarr — read & safe-search examples.
  - `clients/`: NZBGet, SABnzbd, qBittorrent, uTorrent, Deluge, Transmission, BitTorrent — read-only queue examples.
  - `scrapers/`: Prowlarr, Jackett — read-only indexer/status examples.
  - `notifications/`: Apprise — notifications integration (requires `apprise==1.9.4`).

Notes: These plugins are experimental and intended for development and UI testing. Remote actions that can modify upstream databases are disabled by default and gated behind the `allow_remote_actions` config flag. Back up upstream service databases before enabling remote actions.

### Notes for contributors

- If you run the developer pipeline locally, use the project's `.venv` and install the dev tools there (mypy, pytest-cov, etc.) to avoid system package manager restrictions.
- If you'd like me to push the verified changes to `development` and watch CI, I can do that next — confirm and I'll push and monitor the workflows.

## 2025-10-23

### Major Features Added

- **Health and Metrics Endpoints**
  - `/health` and `/metrics` endpoints are now available on the combined service (web UI + scheduler) and are exposed on port `2929`.
  - Designed for Docker healthchecks, monitoring, and debugging.
  - See `docs/Health-and-Metrics.md` for details and usage examples.

- **Live Log Level Control**
  - The log level for both the app and web UI can now be set from the General Settings page in the web UI.
  - Changes are applied live (no restart required).

### Docker Compose Example
- The recommended healthcheck for the main app is now:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:2929/health"]
    interval: 30s
    timeout: 5s
    retries: 3
  ```

### CI and Docker publishing

- Repository-level CI now runs on every push and every pull request via `.github/workflows/ci.yml`. The CI job runs linting, formatting checks, type checks, and the pytest suite. CI uses pip caching to speed up dependency installation.
- Docker images are now built and published for all branches to GitHub Container Registry (GHCR). Images are tagged by branch name (for example `ghcr.io/wikid82/researcharr:feature-xyz` and `ghcr.io/wikid82/researcharr:branch-feature-xyz`). Special tags are still pushed for `main` (`:latest`) and `development` (`:development`). Docker builds use GitHub Actions caching for build layers to accelerate subsequent builds.


### Refactoring and Naming
- Renamed `app.py` to `researcharr.py` for clarity and project consistency.
- Updated all references in README, wiki, and documentation to use `researcharr.py` instead of `app.py`.
- Removed the old `app.py` file from the repository.

### Security / Web UI credentials

- Default web UI username changed to `researcharr` for improved clarity.
- On first startup (when `config/webui_user.yml` does not exist) a secure random password is generated and its plaintext value is logged once to the application logs. The password hash is stored in `config/webui_user.yml` for subsequent runs.
- A new password reset endpoint is available at `/reset-password`. To enable unauthenticated resets via the web UI, set the environment variable `WEBUI_RESET_TOKEN` to a secret value; the reset form must include that token to accept a reset. If `WEBUI_RESET_TOKEN` is not set the reset page is disabled.

### Configuration migration

- PUID, PGID and Timezone are now configured via environment variables (`PUID`, `PGID`, `TIMEZONE`) rather than through the web UI. This prevents permission/timezone mismatches with host-mounted volumes. The General Settings page now shows these values as read-only and documents the env var names. After upgrading, set these env vars and restart your container.

### Documentation
- README.md updated to document health/metrics endpoints, Docker healthcheck, live loglevel control, and the new `researcharr.py` entry point.
- New docs page: `Health-and-Metrics.md` (moved from the wiki).
- All relevant usage and configuration docs updated.

## 2025-10-27

### System / Status and Monitoring

- Added a System → Status page that surfaces operator-facing warnings for common operational problems including storage mounts, database connectivity, configuration/API key issues, first-run admin credentials, permissions, plugin error rates, log growth, external rate-limits, high resource usage, container restarts, and missing example files.
- Implemented a lightweight `/api/status` aggregator endpoint that returns storage, DB, config, logs, resources, metrics and per-plugin summaries used by the UI.
- Added per-plugin in-memory metrics counters (validate/sync attempts and errors) and included an error-rate summary in `/api/status` so repeated plugin failures are surfaced as warnings.
- Added `docs/Status-and-Warnings.md` describing each warning and step-by-step remediation instructions. The Status UI links to the relevant docs sections for each warning.
- Notes: plugin metrics are stored in-memory (reset on restart). Network-heavy checks (update availability, external checks) are opt-in to avoid flaky UI behavior.

### Packaging & CI (consolidation)

- Consolidated image strategy: CI and publishing now focus on a single Debian-slim based production image (`:prod`) plus a debug variant (`:dev`) built from the same multistage `Dockerfile`. This simplifies image maintenance and keeps glibc compatibility for manylinux wheels while providing a debug image with common troubleshooting tools.
- The previous separate `alpine` and `distroless` variants are no longer the primary CI targets; CI now builds and validates `prod` and `dev` variants and runs Trivy checks during validation. Existing Dockerfiles for alternative variants were left in the repo for reference but are not actively published by default.
 - Notes: plugin metrics are stored in-memory (reset on restart). Network-heavy checks (update availability, external checks) are opt-in to avoid flaky UI behavior.

### Backups & Tasks

- Added a Backups UI and API for operator-driven import/export and restore of application state.
  - Backups are compressed tar (.tar.gz) archives stored under the configured `CONFIG_DIR` (default `/config/backups`) and include configuration files, the SQLite DB, plugins directory, and application logs.
  - Supported operations: create, import, download, restore, and delete backups via the web UI and `/api/backups` endpoints.
  - Backups retention and rotation are configurable via `CONFIG_DIR/backups.yml` (keys include `retain_count`, `retain_days`, `pre_restore`, `pre_restore_keep_days`, `auto_backup_enabled`, `auto_backup_cron`, and `prune_cron`).
  - Pre-restore snapshots are taken (opt-in) before a destructive restore and are prefixed `pre-` to help operators recover if a restore fails.

- Added server-side scheduled pruning (rotation) and optional scheduled automatic backups. These are wired to the scheduler and use cron expressions stored in `backups.yml`.

- Persisted Tasks history and settings so scheduled/long-running task runs can be inspected later via `CONFIG_DIR/task_history.jsonl` and `CONFIG_DIR/tasks.yml`.

### Logs and Live Streaming

- Added a dedicated Logs page (`/logs`) with these features:
  - Tail and view the application log (configurable number of lines) and download the full log file.
  - Live log-level control applied at runtime (no restart required). UI-chosen LogLevel is persisted to `CONFIG_DIR/general.yml` so it survives restarts.
  - Optional Server-Sent Events (SSE) streaming endpoint at `/api/logs/stream` to receive initial tail and appended log lines in real-time.

### Updates & Release Checks

- Implemented server-side caching and exponential backoff for release checks (cache persisted at `CONFIG_DIR/updates_cache.yml`, TTL configurable via `UPDATE_CACHE_TTL`). This reduces GitHub API load and handles transient failures gracefully.
- Added API endpoints to: list current release info (`/api/updates`), ignore/unignore releases, and a guarded in-app upgrade download that stores downloaded assets in `CONFIG_DIR/updates/downloads` when allowed (disabled when running inside immutable images).


---

For previous changes, see the project commit history.