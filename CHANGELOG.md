# Changelog

## 2025-10-23

### Major Features Added

- **Health and Metrics Endpoints**
  - `/health` and `/metrics` endpoints are now available in both the main app and the web UI.
  - Designed for Docker healthchecks, monitoring, and debugging.
  - See the new `Health-and-Metrics.md` wiki page for details and usage examples.

- **Live Log Level Control**
  - The log level for both the app and web UI can now be set from the General Settings page in the web UI.
  - Changes are applied live (no restart required).

### Docker Compose Example
- The recommended healthcheck for the main app is now:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
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

### Documentation
- README.md updated to document health/metrics endpoints, Docker healthcheck, live loglevel control, and the new `researcharr.py` entry point.
- New wiki page: `Health-and-Metrics.md`.
- All relevant usage and configuration docs updated.

---

For previous changes, see the project commit history.