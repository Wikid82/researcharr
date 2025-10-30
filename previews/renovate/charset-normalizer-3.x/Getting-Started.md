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

Important note about bind-mounting `/app`

If you mount a host directory onto `/app` (for example in a development compose where you mount your source tree into the container), files that were baked into the image at `/app` will be hidden by the mount. In particular, the bundled `config.example.yml` lives at the repository root and will be available at `/app/config.example.yml` inside the image — but it will be hidden if you mount another host folder over `/app` that doesn't contain the example file.

Recommendations:

- For production/operator usage: do not mount `/app`. Mount only `./config` to `/config` so the entrypoint can copy `/app/config.example.yml` into `/config/config.yml` on first-run.
- For development: mount your repository root into `/app` (for example `- ./:/app:delegated`) so that `/app/config.example.yml` remains present and you can edit source files on the host.
- Quick workaround if you must mount a host folder that does not contain `config.example.yml`: copy `config.example.yml` from the repository into the host path you are mounting, or copy the example into your host `./config/config.yml` before starting the container.
	Scheduling note: the app uses an in-process scheduler (APScheduler) to run the background processing according to a cron-like scheduler expression stored in `config.yml`. Edit this expression from the Scheduling tab in the web UI or directly in `config.yml`.

Health & Metrics

- researcharr exposes `/health` and `/metrics` on port `2929` for monitoring and Docker healthchecks.

Support

- See the `Roadmap.md` and other files in this `docs/` folder for additional project information. See `FAQ.md` for common questions and quick troubleshooting.

If you still have questions, open an issue on GitHub.
