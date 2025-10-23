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


### Refactoring and Naming
- Renamed `app.py` to `researcharr.py` for clarity and project consistency.
- Updated all references in README, wiki, and documentation to use `researcharr.py` instead of `app.py`.
- Removed the old `app.py` file from the repository.

### Documentation
- README.md updated to document health/metrics endpoints, Docker healthcheck, live loglevel control, and the new `researcharr.py` entry point.
- New wiki page: `Health-and-Metrics.md`.
- All relevant usage and configuration docs updated.

---

For previous changes, see the project commit history.