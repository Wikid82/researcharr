# Changelog

This file is the canonical project changelog intended for release notes and recorded history.

For a short, contributor-focused summary of the most recent changes (formatting/CI/Docker/docs), see `docs/Recent-Changes.md` — that file is intended to help contributors triage CI failures and understand what changed quickly.

## 2025-10-23

### Major Features Added
- **Health and Metrics Endpoints**: `/health` and `/metrics` endpoints for both the main app and web UI. Designed for Docker healthchecks, monitoring, and debugging. See `docs/Health-and-Metrics.md` for details.
- **Live Log Level Control**: Log level for both the app and web UI can now be set from the General Settings page in the web UI. Changes are applied live (no restart required).
- **Documentation**: README and docs/wiki updated to document new endpoints, Docker healthcheck, and live loglevel control.

- **CI & Docker publishing**: Added a repository-level CI workflow (`.github/workflows/ci.yml`) that runs linting, type-checks and tests on every push and pull request. CI uses pip caching to speed runs. Docker images are built and published for all branches to GHCR and tagged by branch name; `main` and `development` still receive `:latest` and `:development` tags respectively. Docker build caching is enabled to accelerate subsequent builds.

---

For previous changes, see the project commit history.
