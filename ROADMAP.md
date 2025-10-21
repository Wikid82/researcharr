# Project Roadmap

## 1. Core Architecture
- Modular design: Each *arr integration (Radarr, Sonarr, etc.) as a separate module/class.
- Plugin system: Easy addition of new indexers, download clients, or notification services.
- Central YAML config: All settings in one place, with per-module overrides.

## 2. Feature Set
- Flexible search/upgrade logic (custom rules, tags, quality, custom formats).
- User-defined workflows (e.g., search, notify, upgrade).
- Built-in scheduler (cron-like) and manual/one-off runs via CLI or web UI.

## 3. Extensibility
- REST API for control and monitoring.
- Webhook support for external triggers.
- Modular notification system (Discord, Slack, email, etc.).
- User-configurable notification rules.

## 4. User Experience
- Web UI dashboard for status, logs, and manual actions.
- Config editor and test tools.
- CLI tool for advanced users and scripting.

## 5. Reliability & State
- Use SQLite or Postgres for persistent state (processed items, history, user settings).
- Structured, per-module logs with log levels and rotation.

## 6. Deployment
- Official Docker image with health checks.
- Example docker-compose.yml for easy deployment.
- Cross-platform compatibility (Linux, Windows, macOS).

## 7. Testing & Quality
- Unit and integration tests for all modules.
- CI/CD (GitHub Actions) for linting, testing, and publishing Docker images.

---

## Example Implementation Steps
1. Refactor current code into modular classes for each *arr service.
2. Abstract config loading to support per-module and global settings.
3. Implement a plugin loader for indexers/notifications.
4. Add a REST API (e.g., with FastAPI or Flask).
5. Build a simple web UI (React, Vue, or Flask templates).
6. Add notification modules (start with Discord or email).
7. Switch to a robust DB for state/history.
8. Write tests and set up CI.
9. Polish Docker deployment and documentation.

