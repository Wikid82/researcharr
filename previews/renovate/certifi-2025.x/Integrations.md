# Integrations

This page documents the example integrations (plugins) bundled with ResearchArr and provides links to upstream documentation and setup notes.

Important: these are example/test plugins intended for development and experimentation. Some plugins may attempt network calls when configured. Remote actions that modify state (search, refresh) are disabled by default and gated behind the `allow_remote_actions` flag in the plugin config — set this to `true` only after you have backups and are comfortable testing against a live service.

## Where the plugins live

Plugins are grouped under `plugins/` by category:

- `plugins/media/` — Radarr, Sonarr, Lidarr, Readarr, Whisparr, Headphones, Sick Beard, SickRage, Mylar3, Bobarr
- `plugins/clients/` — NZBGet, SABnzbd, qBittorrent, uTorrent, Deluge, Transmission, BitTorrent (read-only queue)
- `plugins/scrapers/` — Prowlarr, Jackett (indexer aggregators)
- `plugins/notifications/` — Apprise (notifications)

Each plugin implements a small `Plugin` class and may optionally expose a Flask `Blueprint` for UI endpoints. Common endpoints:

- `GET /plugin/<name>/items` or `/queue` — returns the instance's DB-derived items or queue.
- `GET /plugin/<name>/info` — returns plugin config and metadata.
- `POST /plugin/<name>/search` — triggers a search; remote actions are simulated unless `allow_remote_actions` is enabled.

## Setup notes & links

These are links to upstream projects and hints for configuring them:

- Radarr — https://radarr.video/ — API: `/api/v3/` (set API key and base URL in plugin config)
- Sonarr — https://sonarr.video/ — API: `/api/v3/` (supports series/season/episode search via `/api/v3/command` or episode-level endpoints)
- Lidarr — https://lidarr.audio/ — music-focused, API similar to Radarr/Sonarr
- Readarr — https://readarr.com/ — books-focused
- Whisparr — https://github.com/Whisparr/Whisparr
- Headphones — https://github.com/rembo10/headphones
- Sick Beard / SickRage — legacy TV indexers; check their APIs exposed at `/api`
- Mylar3 — https://github.com/mylar3/mylar3 — comics handling
- Bobarr — https://github.com/Bobarr/Bobarr — a small Radarr-like project

- NZBGet — https://nzbget.net/ — JSON-RPC usually at `/jsonrpc` or `/api`
- SABnzbd — https://sabnzbd.org/ — API: `/api?mode=queue&output=json&apikey=<key>`

- qBittorrent — https://www.qbittorrent.org/ — API v2 (login + `/api/v2/torrents/info`)
- uTorrent — https://www.utorrent.com/ — web UI API varies (best-effort read-only support)
- Deluge — https://deluge-torrent.org/ — web API available at `/json`
- Transmission — https://transmissionbt.com/ — RPC endpoint via POST JSON

- Prowlarr — https://github.com/Prowlarr/Prowlarr — API v1 `/api/v1/indexer` or `/api/v1/status`
- Jackett — https://github.com/Jackett/Jackett — API v2 `/api/v2.0/indexers` or `/api/v2/indexers`

- Apprise — https://github.com/caronc/apprise — Python package used to send notifications; install via `pip install apprise` (we pin `apprise==1.9.4` in `requirements.txt`).

## Backup & safety

These plugins are experimental. Before enabling remote actions against production services, ensure you have backups of the services' databases and configurations. For example:

- Back up Radarr/Sonarr: stop the service, back up the SQLite database files and config folders.
- Back up qBittorrent/Deluge/Transmission configs and watch folders before enabling remote writes.

If you are testing with production services, run with `allow_remote_actions` disabled until you have validated behavior in a staging environment.

## Troubleshooting

- If a plugin returns mocked data, ensure the plugin config (`url`, `api_key`, etc.) is populated correctly.
- For network issues, run the app in the developer container and use curl/wget from inside to verify connectivity to the service.

## Contributing

If you implement or improve an integration, please add tests under `tests/` that mock network calls and validate both the happy path and fallback behavior.
