# Logs and Live Streaming

This page documents the new Logs UI and APIs added to the web UI.

What it provides

- A Logs page in the web UI (`/logs`) where operators can:
  - View the application log (tail the last N lines).
  - Download the full application log file.
  - Set the live logging level for the running process (no restart required).
  - Optionally enable a live Server-Sent Events (SSE) stream to receive new log lines as they are written.

APIs

- GET /api/logs?lines=200
  - Returns JSON: { content: <string>, meta: {path,size,mtime}, loglevel: <current> }
  - `lines` (optional) controls how many tail lines to return (default 200).

- GET /api/logs?download=1
  - Returns the log file as a download attachment.

- GET /api/logs/stream?lines=200
  - Server-Sent Events (SSE) endpoint. Sends an initial tail of `lines` lines, then streams appended lines as `data:` events.
  - Clients should connect using `EventSource('/api/logs/stream?lines=200')` (same-origin cookies used for authentication).

- POST /logs
  - Accepts form-encoded `LogLevel=<level>` and updates the running process log level (applied to the root logger and `app.logger`).
  - Also persists the UI-chosen LogLevel to `CONFIG_DIR/general.yml` so it survives restarts.

Configuration and files

- Log file path consulted by the UI/APIs:
  - `WEBUI_LOG` environment variable, or fallback to the repository `app.log` path.
  - Example: `WEBUI_LOG=/config/app.log`

- Persisted UI-chosen settings:
  - `CONFIG_DIR/general.yml` (only contains `LogLevel` to avoid clobbering env-managed keys).

Security and notes

- All endpoints above require a logged-in session (same authentication as other UI pages).
- The SSE endpoint uses a simple polling loop to detect appended lines when inotify is not available. Browsers will auto-reconnect if the connection drops.
- The server-side tail implementation reads file blocks from the end (memory-efficient) before streaming updates.

Recommendations

- If you expect very large logs or many concurrent SSE connections, consider:
  - Rotating logs on the host (logrotate) or using a sidecar to collect logs centrally.
  - Using file-system notifications (inotify) to reduce polling latency (can be implemented server-side).

Examples

- In the browser console:

```js
const es = new EventSource('/api/logs/stream?lines=200');
es.onmessage = e => console.log('log', e.data);
```

- Apply a new log level via curl (authenticated):

```bash
curl -X POST -d 'LogLevel=DEBUG' -u admin:researcharr 'http://localhost:2929/logs'
```
