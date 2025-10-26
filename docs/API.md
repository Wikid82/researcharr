# ResearchArr API (v1)

This document describes the minimal REST API added in `/api/v1`.

Authentication
- Use an API key in the `X-API-Key` header for programmatic access.
- API keys are created on first-run and can be viewed / regenerated in the
  Web UI under Settings → General.

Endpoints

- `GET /api/v1/health` — Basic health check. Returns JSON with `status` and `db` fields.
- `GET /api/v1/metrics` — Returns the application metrics JSON.
- `GET /api/v1/plugins` — (requires API key) Returns discovered plugins and configured instances. Shape: `{ "plugins": [{ "name": "radarr", "instances": [...] }, ...] }`.
- `POST /api/v1/plugins/<plugin>/validate/<idx>` — (requires API key) Run plugin validate for instance index `idx`.
- `POST /api/v1/plugins/<plugin>/sync/<idx>` — (requires API key) Run plugin sync for instance index `idx`.
- `POST /api/v1/notifications/send` — (requires API key) Send a notification using the first configured `apprise` plugin instance. JSON body expects `{ "title": "...", "body": "..." }`.

Security & Safety
- The API is read-only by default for most endpoints; actions that perform remote changes are gated behind plugin behaviour and require an API key.
- If you expose the API externally, terminate TLS at the edge and restrict access.
- The Web UI provides a "Regenerate API Key" button which will persist the new key to the web UI config file so it survives restarts.

Usage example

curl -H "X-API-Key: <your-key>" https://researcharr.local/api/v1/plugins
