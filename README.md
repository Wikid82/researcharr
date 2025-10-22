<p align="center" style="background: rgba(255, 255, 255, 1); padding: 16px; border-radius: 8px;">
  <img src="static/logo.jpg" alt="researcharr logo" height="150"/>
</p>

<p align="center"
![Docker Publish (main)](https://github.com/Wikid82/researcharr/actions/workflows/docker-publish.yml/badge.svg?branch=main)
![Docker Publish (development)](https://github.com/Wikid82/researcharr/actions/workflows/docker-publish.yml/badge.svg?branch=development)
</p>

# researcharr

A modern, always-on utility to automatically trigger searches in the *arr suite to keep files up to date with any scoring or custom format changes. Features a secure, AJAX-powered web UI for managing all settings, per-instance validation, and robust automated test coverage.

## Developer Note: Config Loader & Test Coverage

The `load_config()` function now accepts an optional `path` argument, allowing tests and advanced users to load configuration from any file. This enables robust testing of config edge cases (missing, empty, malformed, or partial configs) and makes it easier to develop and validate new features. The test suite now covers config loading, error handling for connections, database integrity, and logger output.

**Key Features:**
- Modern AJAX web UI (instant navigation, no page reloads)
- Secure login, user management, and error feedback
- Edit all config (including schedule/timezone) from the UI
- Enable/disable and validate up to 5 Radarr & 5 Sonarr instances
- All endpoints and UI behaviors are covered by automated tests

## Project Structure

```
researcharr/
├── config.example.yml
├── .github/
│   └── workflows/
│       └── docker-publish.yml
├── Dockerfile
├── LICENSE
├── README.md
├── app.py
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```


## Requirements

- Python 3.8+
- Docker (for containerized usage)
- [Radarr](https://radarr.video/) and/or [Sonarr](https://sonarr.tv/) instances

All required Python packages are listed in `requirements.txt` and are installed automatically when building or running the Docker container. This includes:

- Flask (for the web UI)
- Werkzeug (for secure login/password hashing)
- PyYAML (for YAML config and user management)

If running outside Docker, install dependencies with:

```bash
pip install -r requirements.txt
```

## How to Use

1.  **Create a configuration directory:**
  ```bash
  mkdir -p /path/to/config
  # You do not need to manually copy config.yml unless you want to pre-configure settings.
  # If /config/config.yml is missing, it will be auto-created from config.example.yml at container startup.
  ```

2.  **Edit your configuration:**
  Open `/path/to/config/config.yml` in your favorite editor and fill in the values for up to 5 Radarr and 5 Sonarr instances, schedule, and timezone. Each instance can be enabled or disabled. All options are documented in the example file. The cron job schedule can also be edited from the "Scheduling" tab in the web UI, with changes reflected in the config and container behavior.

3.  **Run the container:**
    You can use either Docker Compose (recommended) or a `docker run` command. See the examples below. The first time the script runs, it will create a `researcharr.db` file and a `logs` directory inside your config volume.

4.  **Check the logs:**
  Live logs are streamed and can be viewed using the `docker logs` command. See the Logging section for more details.

5.  **Use the Web UI (AJAX-powered, always-on):**
    - Launch with:
      ```bash
      docker exec -it researcharr python3 /app/webui.py
      ```
      Then visit [http://localhost:2929](http://localhost:2929) in your browser.
    - **Login is required.**
      - Default username: `admin`
      - Default password: `researcharr`
      (Change these in production using the "User Settings" tab in the web UI, which updates `webui_user.yml`.)
    - **AJAX navigation:** Sidebar and header never reload; only the main content area updates. All forms and navigation are AJAX-powered for instant feedback.
    - **Per-instance validation:** Each Radarr and Sonarr instance has a "Validate & Save" button for instant connection testing and dry-run, with results shown in the UI.
    - **Error feedback:** All error messages (e.g., invalid config, missing API key) are shown instantly in the UI.
    - **Multi-instance:** Enable/disable and configure up to 5 Radarr and 5 Sonarr instances. All instance settings are collapsed by default; enable to expand and edit.
    - **Always-on:** The container and web UI never exit on invalid config—fix your settings at any time using the web UI.
    - **User credentials:** Managed in `webui_user.yml` and editable from the UI.
    - **Test coverage:** All endpoints and UI behaviors are covered by automated tests.

## Configuration (All Editable in Web UI)

All configuration is now managed in a single YAML file: `/path/to/config/config.yml`.

- See `config.example.yml` for a fully documented template.
- You can set your timezone, cron schedule (or edit both from the Scheduling tab in the web UI), Radarr/Sonarr URLs, API keys, and processing options in this file.
- The Scheduling tab in the web UI now allows you to edit both the cron job schedule and the timezone. Changes are saved to config and used by the app and entrypoint script. See the wiki page [Scheduling and Timezone](wiki/Scheduling-and-Timezone.md) for details.
- Example URLs for Docker default network: `http://radarr:7878` and `http://sonarr:8989`.

## State Management

This application uses a **SQLite database** (`researcharr.db`) to manage a persistent queue of items to process. This ensures that every eligible media file is eventually searched for without repetition.

*   **Workflow:**
    1.  On the first run, or any time the processing queue is empty, the script scans your entire library to find all items that need an upgrade and populates the queue. This can take some time depending on the size of your library.
    2.  On all subsequent runs, the script simply takes the next batch of items from the queue, triggers a search, and removes them from the queue. These runs are very fast.
*   **Persistence:** The database file is stored in your main config volume (`/path/to/config/researcharr.db`), so the queue is maintained even if you restart or update the container.

## Logging

The application creates three separate log files inside a `logs` directory within your main config volume (`/path/to/config/logs/`):

*   `researcharr.log`: Contains general application status, such as starting and finishing a run.
*   `radarr.log`: Contains all logs specifically related to Radarr API calls and processing.
*   `sonarr.log`: Contains all logs specifically related to Sonarr API calls and processing.

You can view a combined, real-time stream of all logs by running:
```bash
docker logs -f researcharr
```

---


docker exec -it researcharr python3 /app/webui.py

## Web UI (AJAX Navigation, Always-On)

**Key Features:**
- **AJAX Navigation:** Sidebar and header never reload; only the main content area updates. All forms and navigation are AJAX-powered for instant feedback.
- **Per-Instance Validation:** Each Radarr and Sonarr instance has a "Validate & Save" button for instant connection testing and dry-run, with results shown in the UI.
- **Error Feedback:** All error messages (e.g., invalid config, missing API key) are shown instantly in the UI.
- **Multi-Instance:** Enable/disable and configure up to 5 Radarr and 5 Sonarr instances. All instance settings are collapsed by default; enable to expand and edit.
- **Always-On:** The container and web UI never exit on invalid config—fix your settings at any time using the web UI.
- **User Credentials:** Managed in `webui_user.yml` and editable from the UI.
- **Test Coverage:** All endpoints and UI behaviors are covered by automated tests.
- **Responsive:** The UI is optimized for both desktop and mobile browsers.

To use the web UI, run:
```bash
docker exec -it researcharr python3 /app/webui.py
```
and visit [http://localhost:2929](http://localhost:2929).

**Dependencies:** Flask, Werkzeug, and PyYAML are required for the web UI and are installed automatically in Docker. If running locally, install them with `pip install -r requirements.txt`.

**User credentials:** Managed in `webui_user.yml` and editable from the "User Settings" tab in the web UI.

### Download Queue Limit & Reprocessing Interval (per instance)

Each Radarr and Sonarr instance now supports:

- `max_download_queue` (default: 15): If the number of items in the instance's download queue is at or above this value, researcharr will skip upgrades for that instance until the next run. This helps prevent overloading your download client.
- `reprocess_interval_days` (default: 7): Items will be reprocessed (searched again) after this many days, even if they were previously processed. This helps ensure upgrades are retried over time. You can edit this value for each instance in the web UI or directly in `config.yml`.

```bash
docker run -d \
  --name=researcharr \
  -v /path/to/config:/config \
  -p 2929:2929 \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:latest
```
**Note:** All configuration is handled in `/path/to/config/config.yml`. If this file is missing, it will be auto-created from `config.example.yml` at container startup. No environment variables or `.env` file are required.

## Important Notes

- The container and web UI will always stay up, even if no valid Radarr/Sonarr config is present. You can fix your configuration at any time using the web UI.
- Each Radarr and Sonarr instance in the web UI now has a "Validate & Save" button. This tests the connection and performs a dry run for that instance, showing the result instantly.
- Radarr and Sonarr URLs must start with `http://` or `https://` and have a valid API key. If not, the instance will be skipped and a warning will be shown in the UI and logs.

