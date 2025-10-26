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

---

For previous changes, see the project commit history.