# Plugins and instance configuration

This project separates plugin *code* from plugin *instance* configuration.

Key points

- Plugin code (Python modules) is part of the repository under `researcharr/plugins/` and must be added via a pull request. We do not support mounting arbitrary Python code into the container — this avoids executing unreviewed code in operator environments.
- Plugin *instance* configuration lives under `/config/plugins/<plugin>.yml` and is persisted on disk. Each file contains a YAML list of instances for that plugin (the UI reads/writes these files).

Operator workflows

- To pre-seed instances before first-run, place YAML files under your host `./config/plugins/` (the repo includes commented example templates under `config/plugins/` you can copy).
- Keep `/config` mounted read-write so the UI can persist changes (user credentials, plugin instance files, general settings, backups, and task history).

Contributing new plugins

- If you want to add new plugin functionality (new plugin module), please open a pull request adding the plugin module under `researcharr/plugins/` and a matching commented example YAML under `config/plugins/` to help operators pre-seed instances.
- The project maintainers will review and merge plugin code. This keeps the codebase secure and auditable.

Security considerations

- Do not enable arbitrary code execution via mounted plugin directories. If you must run third-party plugins, run them only after code review and ideally inside a controlled environment.

Example plugin instance (Sonarr)

```yaml
# /config/plugins/sonarr.yml
- name: "My Sonarr"
  enabled: true
  url: "http://sonarr:8989"
  api_key: "replace-with-key"
  episodes_to_upgrade: 5
  max_download_queue: 15
  reprocess_interval_days: 7
```
