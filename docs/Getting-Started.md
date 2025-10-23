# Getting Started

Follow these steps to run researcharr locally or in Docker.

Local (development)

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app (example):

```bash
python researcharr.py serve
```

Docker

1. Build and run using Docker Compose (example):

```bash
docker-compose up -d --build
```

2. The web UI is available on port `2929` by default.

Security and initial credentials

- On first startup, if `config/webui_user.yml` does not exist, the web UI will create one and set the default username to `researcharr` and generate a secure random password. The plaintext password is logged once to the application logs to allow initial login. The password itself is stored hashed in `config/webui_user.yml`.
- To change credentials after first-run use the User Settings page in the web UI.
- A password reset page is available at `/reset-password`. To enable web-based resets you must set the environment variable `WEBUI_RESET_TOKEN` to a secret value; the reset form must present this token to reset the password. If you do not set this variable, the reset page will display that reset is not available.

Configuration and config files

- See `config.example.yml` for configuration options. The container will auto-create `/config/config.yml` from the example if it's missing.

Health & Metrics

- The app exposes `/health` and `/metrics` for monitoring and Docker healthchecks.

Support

- See the wiki `FAQ.md` and `Roadmap.md` for additional project information.
