# Roadmap

This document summarizes project priorities and the near-term roadmap.

Key priorities

- App-first focus: Prioritize core app features and stability over major UI redesigns.
- Move away from cron-only scheduling: Explore event-driven or sidecar approaches (WebSockets / scheduler service).
- WebSocket support for UI: Replace some polling with real-time updates where useful.
- Release-aware processing: Allow runs to behave differently for release builds and avoid noisy updates.
- Notifications: Webhook and Apprise integrations for alerts.
- Packaging & Distribution: See `docs/Packaging-and-Distribution.md` for details and priorities.

If you'd like to propose changes to the roadmap, open an issue or PR describing the change and rationale.
