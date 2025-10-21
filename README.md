# researcharr

A utility to automatically trigger searches in the *arr suite to keep files up to date with any scoring or custom format changes.

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

## How to Use

1.  **Create a configuration directory:**
    ```bash
    mkdir -p /path/to/config
    cp config.example.yml /path/to/config/config.yml
    ```

2.  **Edit your configuration:**
    Open `/path/to/config/config.yml` in your favorite editor and fill in the values for your Radarr and/or Sonarr instances, schedule, and timezone. All options are documented in the example file.

3.  **Run the container:**
    You can use either Docker Compose (recommended) or a `docker run` command. See the examples below. The first time the script runs, it will create a `researcharr.db` file and a `logs` directory inside your config volume.

4.  **Check the logs:**
  Live logs are streamed and can be viewed using the `docker logs` command. See the Logging section for more details.

5.  **(Optional) Use the Web UI:**
  A simple web interface is available for editing settings and testing connections. After starting the container, run:
  ```bash
  docker exec -it researcharr python3 /app/webui.py
  ```
  Then visit [http://localhost:2929](http://localhost:2929) in your browser.
  The web UI allows you to edit config.yml and test Radarr/Sonarr connections directly.

## Configuration

All configuration is now managed in a single YAML file: `/path/to/config/config.yml`.

- See `config.example.yml` for a fully documented template.
- You can set your timezone, cron schedule, Radarr/Sonarr URLs, API keys, and processing options in this file.
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


## Web UI

The web UI runs on port **2929**. To use it, run:
```bash
docker exec -it researcharr python3 /app/webui.py
```
and visit [http://localhost:2929](http://localhost:2929).

---

## Docker Compose Example

This is the recommended way to run the application.

```yaml
---
services:
  researcharr:
    image: ghcr.io/wikid82/researcharr:latest
    container_name: researcharr
    restart: unless-stopped
    ports:
      - "2929:2929" # Expose web UI on port 2929
    volumes:
      - /path/to/config:/config # This directory will contain your config.yml, logs/, and researcharr.db
    depends_on:
        <download_client>:
          condition: service_started
        radarr:
          condition: service_started
        sonarr:
          condition: service_started
    deploy:
        resources:
          limits:
            cpus: '1.0'
            memory: 2G
          reservations:
            cpus: '0.5'
            memory: 512M
```

## Docker Run Example

```bash
docker run -d \
  --name=researcharr \
  -v /path/to/config:/config \
  -p 2929:2929 \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:latest
```
**Note:** All configuration is now handled in `/path/to/config/config.yml`. No environment variables or `.env` file are required.
