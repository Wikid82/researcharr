# System status warnings and how to fix them

This page documents the various warnings the web UI can surface on the System → Status page and provides concrete remediation steps and examples.

Each status warning includes a short description, how it's detected, common causes, and step-by-step instructions to resolve the issue. Use the links from the Status UI to jump to the relevant section.

Table of contents
- Storage mounts (/config, /config/plugins)
- Database connectivity
- Configuration and API key
- Admin credentials (first-run plaintext)
- Permissions on mounted directories
- Plugin error-rate
- Log file growth
- Update available (opt-in)
- External service rate-limits
- High resource usage
- Container restarts
- Missing example files
- /api/status aggregator

- Backups and retention
- Tasks persistence

## Storage mounts

Anchor: `#storage-mounts`

What it means
: The application cannot access one or more configured filesystem paths (typically `/config` and `/config/plugins`). This may be reported as the path not existing, not being a directory, or lacking read/write permissions.

How we detect it
: The UI calls the backend `/api/status` (and `/api/storage`) which checks `os.path.exists`, `os.path.isdir`, and `os.access` for read/write.

Common causes
- The host directory was not bind-mounted into the container (missing `-v /host/path:/config`).
- The container user (UID/GID) lacks permissions to read/write the mounted folder.
- `CONFIG_DIR` env var points to a non-existent path.

How to fix
1. If you run via `docker run`, mount a host path to `/config`:

```bash
docker run -d \
  -v /path/on/host:/config \
  -e PUID=1000 -e PGID=1000 \
  -p 2929:2929 ghcr.io/Wikid82/researcharr:latest
```

2. If you use `docker-compose`:

```yaml
services:
  researcharr:
    image: ghcr.io/Wikid82/researcharr:latest
    volumes:
      - ./config:/config
```

3. Fix permissions on the host (adjust UID/GID to your container user):

```bash
sudo chown -R 1000:1000 /path/on/host
sudo chmod -R u+rwX /path/on/host
```

4. If your deployment uses a non-standard config location, set `CONFIG_DIR` accordingly.

More details: See the Status UI storage help modal for copyable examples.

## Database connectivity

Anchor: `#database-connectivity`

What it means
: The web UI cannot open or query the SQLite database file used by the service. This may prevent scheduled jobs and plugin persistence from working.

How we detect it
: The aggregator attempts a lightweight `SELECT 1` against the configured DB file path (env `RESEARCHARR_DB` or the repository default). Errors are surfaced in `/api/status`.

Common causes
- DB file missing or moved
- File permission problems
- Database file corrupt

How to fix
1. Check the configured DB path and ensure it exists and is readable by the container process.
2. Inspect the DB file: `sqlite3 /config/researcharr.db "PRAGMA integrity_check;"` — if it returns anything other than `ok`, consider restoring from backup.
3. If the file is corrupt, restore your latest backup and restart the service.
4. If you cannot restore, consider exporting critical data with `sqlite3` and recreating the DB.

## Configuration and API key

Anchor: `#configuration-and-api-key`

What it means
: The app detected missing or incomplete configuration values such as a missing `api_key_hash` or other critical settings.

How we detect it
: The aggregator inspects `app.config_data` and the persisted `webui_user.yml` for missing keys.

Common causes
- First-run state where an API key was not generated or persisted
- Migration edge-cases where keys were not carried forward

How to fix
1. Open Settings → General in the web UI and regenerate the API key if needed.
2. Persist the key securely — the web UI stores only a hash (`api_key_hash`).

## Admin credentials (first-run plaintext)

Anchor: `#admin-credentials`

What it means
: On first-run the app generates a random admin password and keeps the plaintext in-memory to allow initial login. The status page warns you to rotate it once you have logged in.

How we detect it
: We check if the in-memory `app.config_data.user` contains a plaintext `password` and no `password_hash`.

How to fix
1. Log in using the generated credentials, then set a permanent password via Settings → User. This will persist a hashed password.
2. If you exposed the plaintext via logs or console, rotate the password immediately.

## Permissions on mounted directories

Anchor: `#permissions`

What it means
: Even when a host path is mounted, the container user may not have the required read/write permissions.

How to fix
: See the Storage section above; `chown`/`chmod` examples are provided. Prefer setting PUID/PGID environment variables to match host ownership.

## Plugin error-rate

Anchor: `#plugin-error-rate`

What it means
: A plugin's validation/sync endpoints are failing frequently. The status page computes an error rate: when a plugin has repeated failures the UI will show a warning.

How we detect it
: The UI calls plugin `validate` endpoints to test connectivity. The backend also tracks per-plugin attempts/errors in memory and reports an error rate via `/api/status`.

Common causes
- Incorrect endpoint URL or API key for the upstream service
- Network problems or firewall blocking
- The remote service is overloaded or returning 4xx/5xx responses

How to fix
1. Open Settings → Plugins and inspect the plugin instance configuration.
2. Use the Retry button on the Status page to re-run validation.
3. Check upstream service logs and credentials; if a remote API is rate limiting you, consider reducing polling frequency.

## Log file growth

Anchor: `#log-growth`

What it means
: The application log file has grown beyond the threshold (default 5 MB recommended threshold), which may indicate noisy errors or misconfiguration.

How we detect it
: `/api/status` reports the size of `app.log` and the status page warns when it exceeds the threshold.

How to fix
1. Rotate or truncate the log file: `truncate -s 0 /config/app.log` (do this only when safe to do so).
2. Investigate the root cause of new log entries (use Settings → Logs and the `/logs` page).
3. Consider log rotation via the host or a sidecar.

More: See `docs/Logs.md` for details on the Logs UI, live log-level control, and the SSE streaming endpoint (`/api/logs/stream`).

## Update available (opt-in)

Anchor: `#update-available`

What it means
: An update checker can optionally compare the running version to the latest release. This check is opt-in to avoid unexpected network calls.

How to enable
: Configure the update check in your deployment or enable via environment flags (not enabled by default by design).

## External service rate-limits

Anchor: `#external-rate-limits`

What it means
: External services (indexers, Radarr/Sonarr, etc.) may return 429 or other rate-limiting responses. The backend can surface repeated 429s as a warning.

How to fix
: Reduce polling frequency, add exponential backoff in upstream services, or request higher rate limits from the provider.

## High resource usage

Anchor: `#high-resource-usage`

What it means
: The host/container is experiencing high memory or CPU usage which can impact responsiveness.

How we detect it
: The aggregator reads `/proc` (when available) to compute memory usage and load averages. When memory usage exceeds a conservative threshold, a warning appears.

How to fix
: Reduce concurrent workloads, increase container resource limits, or move to a larger host.

## Container restarts

Anchor: `#container-restarts`

What it means
: Frequent container restarts can indicate a crash loop or failing healthcheck.

How to detect
: Detecting restarts reliably requires orchestration metadata (Docker, Kubernetes). The app can use heuristics (uptime vs. persisted timestamp) but this is best observed in container runtime logs.

How to fix
: Inspect container logs (`docker logs <container>`), adjust healthcheck, and fix the underlying exception.

## Missing example files

Anchor: `#missing-example-files`

What it means
: The repository's example config files (e.g. `config.example.yml`) are missing from the deployment. Examples are harmless but useful references for manual configuration.

How to fix
: Re-populate example files from the repository or view them on the project's docs.

## /api/status aggregator

Anchor: `#api-status-aggregator`

What it returns
: The endpoint `/api/status` returns a JSON object with keys for `storage`, `db`, `config`, `logs`, `examples`, `resources`, `metrics`, and `plugins`.

Usage
: The Status UI uses `/api/status` to render non-plugin warnings in a single call. The endpoint is authenticated (requires a valid session).

Notes
- The checks are intentionally lightweight and best-effort. Network-heavy checks are opt-in to avoid flaky UI behaviour.
- Plugin metrics are stored in-memory and reset on service restart unless you enable persistence via a custom implementation.


## Backups and retention

Anchor: `#backups-and-retention`

What it means
: The application exposes a Backups page and `/api/backups` endpoints for creating, importing, downloading, restoring and deleting backup ZIP archives representing application state.

How we detect issues
: The Status UI and backups page surface failures to create or import archives, and the backend logs any I/O or integrity errors. Scheduled pruning failures are surfaced in the application logs and the Status UI may show related warnings when backups cannot be rotated or created.

Common causes
- Missing or unwritable `CONFIG_DIR` (default `/config`) or `CONFIG_DIR/backups` directory.
- Insufficient disk space when creating large backups.
- Corrupt or malformed imported ZIP files.

How to fix
1. Check that the backups folder is present and writable by the container process (see Storage mounts section). Example:

```bash
ls -la /config/backups
sudo chown -R 1000:1000 /path/to/config
```

2. If imports fail with integrity errors, inspect the archive contents locally and re-create a valid ZIP from a known-good copy.

3. Configure retention and scheduling in `CONFIG_DIR/backups.yml`. Key settings:
  - `retain_count`: keep most recent N backups
  - `retain_days`: keep backups younger than N days
  - `pre_restore`: when enabled, create an automatic snapshot before a restore
  - `pre_restore_keep_days`: retention window for pre-restore snapshots
  - `auto_backup_enabled`: enable scheduled automatic backups
  - `auto_backup_cron` / `prune_cron`: cron expressions for auto-backup and scheduled pruning

Notes
- Pre-restore snapshots are prefixed with `pre-` and, by default, are retained for a short window (see `pre_restore_keep_days`) so you can recover from failed restores.


## Tasks persistence

Anchor: `#tasks-persistence`

What it means
: The scheduler records task run history and settings so you can inspect past runs and failures from the Tasks page in the UI. History is persisted to `CONFIG_DIR/task_history.jsonl` and settings to `CONFIG_DIR/tasks.yml`.

How we detect issues
: The Status UI surfaces if task history cannot be written (I/O errors) or if scheduled jobs fail repeatedly. Check application logs for task-related exceptions.

How to fix
1. Ensure `CONFIG_DIR` is writable and has sufficient disk space.
2. If the history file is corrupt, you can rotate or remove it; historic runs will be lost but the scheduler will continue creating new history entries.
3. For repeated scheduled job failures, inspect the task details in the Tasks page and consult logs for stack traces.

---

If a remediation step isn't working for your environment, open an issue with the following information:
- deployment method (docker run / docker-compose / k8s)
- output of `docker logs` (or systemd logs)
- relevant config files (sanitized)

Thank you for helping make the project more robust — file an issue if you need step-by-step help.
