# researcharr

A utility to automatically trigger searches in the *arr suite to keep files up to date with any scoring or custom format changes.

## Project Structure

```
researcharr/
├── .example_env
├── .github/
│   └── workflows/
│       └── docker-publish.yml
├── Dockerfile
├── LICENSE
├── README.md
├── app.py
├── cronjob.template
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```

## How to Use

1.  **Create a configuration directory:**
    ```bash
    mkdir -p /path/to/config
    ```

2.  **Create and configure your `.env` file:**
    Create a file named `.env` inside your new config directory (`/path/to/config/.env`). Copy the contents from `.example_env` and fill in the values for your Radarr and/or Sonarr instances.

3.  **Run the container:**
    You can use either Docker Compose (recommended) or a `docker run` command. See the examples below.

## Environment Variables

| Variable                  | Description                                                                                             | Default Value       |
| ------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------- |
| `PROCESS_RADARR`          | Set to `true` to process Radarr.                                                                        | `false`             |
| `PROCESS_SONARR`          | Set to `true` to process Sonarr.                                                                        | `false`             |
| `RADARR_API_KEY`          | Your Radarr API key.                                                                                    | `your_api_key_here` |
| `SONARR_API_KEY`          | Your Sonarr API key.                                                                                    | `your_api_key_here` |
| `RADARR_URL`              | The full URL to your Radarr instance (e.g., `http://127.0.0.1:7878`).                                | `""`                |
| `SONARR_URL`              | The full URL to your Sonarr instance (e.g., `http://127.0.0.1:8989`).                                | `""`                |
| `NUM_MOVIES_TO_UPGRADE`   | The number of movies to search for in each run.                                                         | `5`                 |
| `NUM_EPISODES_TO_UPGRADE` | The number of episodes to search for in each run.                                                       | `5`                 |
| `CRON_SCHEDULE`           | The cron schedule for how often to run the script.                                                      | `* * * * *`         |
| `TZ`                      | Your timezone (e.g., `America/Los_Angeles`).                                                            | `""`                |

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
    environment:
      - CRON_SCHEDULE=* * * * *
      - TZ=America/Los_Angeles
    volumes:
      - /path/to/config:/config # This directory should contain your .env file
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
  -e CRON_SCHEDULE="* * * * *" \
  -e TZ="America/Los_Angeles" \
  -v /path/to/config:/config \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:latest
```
**Note:** The `docker run` command uses environment variables set directly in the command. The application itself will load the *arr-specific variables from the `.env` file located in your `/path/to/config` volume.
