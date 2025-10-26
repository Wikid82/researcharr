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

Runtime variants

The project publishes two runtime variants: `distroless` (recommended for production, minimal runtime) and `alpine` (developer-friendly). For production runs use the `distroless` image and mount a persistent `/config` directory. For development, use `alpine` or the `builder` stage so you have a shell and dev tooling available.

- Security and initial credentials

- On first startup, if `config/webui_user.yml` does not exist, the web UI will create one and set the default username to `researcharr` and generate a secure random password. The plaintext password is logged once to the application logs to allow initial login; the password hash is stored in `config/webui_user.yml`.
- Note: the initial password generation runs when the web UI code is initialized (on full web UI startup). If you run only a one-shot scheduler job (for example using `run.py --once`) the web UI won't be initialized and the user file will not be created. To create the file and see the generated password in logs, start the full app (detached or foreground) so the web UI initializes.
- To change credentials after first-run use the User Settings page in the web UI.
- A password reset page is available at `/reset-password`. To enable web-based resets you must set the environment variable `WEBUI_RESET_TOKEN` to a secret value; the reset form must present this token to reset the password. If you do not set this variable, the reset page will display that reset is not available.

Configuration and config files

- See `config.example.yml` for configuration options. The container will auto-create `/config/config.yml` from the example if it's missing.
	Scheduling note: the app uses an in-process scheduler (APScheduler) to run the background processing according to a cron-like scheduler expression stored in `config.yml`. Edit this expression from the Scheduling tab in the web UI or directly in `config.yml`.

Health & Metrics

- researcharr exposes `/health` and `/metrics` on port `2929` for monitoring and Docker healthchecks.

Support

- See the `Roadmap.md` and other files in this `docs/` folder for additional project information. See `FAQ.md` for common questions and quick troubleshooting.

If you still have questions, open an issue on GitHub.
