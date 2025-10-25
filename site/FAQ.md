````markdown
# FAQ — researcharr

This page collects short answers to common questions about running and operating researcharr.

## Q: Is there an FAQ in this repo?
A: Yes — this file (`docs/FAQ.md`) contains common questions and answers. If you relied on the old wiki FAQ, the most common items have been copied here.

## Q: Where do I find detailed docs?
A: Full documentation lives in the `docs/` folder of this repository. The site is published to GitHub Pages from `docs/` on the `main` branch.

## Q: What happened to the web UI initial password?
- On first startup (when `config/webui_user.yml` does not exist) a secure username (`researcharr`) and a random password are generated. The plaintext password is logged once in the container logs for operator convenience; only the hash is stored in `config/webui_user.yml`.
- If you need to see the generated password, start the full web UI (not a one-shot scheduler run) and inspect the container logs. Example:

```bash
docker logs --tail 200 researcharr | grep -i "Generated web UI initial password" -A1 -B1
```

## Q: How do I reset the web UI password?
- A password reset endpoint exists. To allow unauthenticated resets via the web UI, set the environment variable `WEBUI_RESET_TOKEN` to a secret value before starting the container. Without it the reset page will be disabled and only authenticated users can change passwords.

## Q: Why do I need to set `SECRET_KEY`? What if I don't have it?
- For production deployments (`ENV=production` or running under a WSGI server) you must set `SECRET_KEY` in the environment. This prevents session tampering and is required by Flask/Werkzeug.
- In development (`FLASK_ENV=development` or running locally), a temporary key may be generated but it is not secure for production.

## Q: How should I set PUID/PGID and timezone?
- PUID, PGID, and TIMEZONE are configured by environment variables (`PUID`, `PGID`, `TIMEZONE`). This avoids host/container permission mismatches on mounted volumes and ensures scheduling uses your desired timezone. See `docs/Environment-Variables.md` for examples.

## Q: What port does the web UI use?
- The web UI bind port is configurable via `WEBUI_PORT` (default: 2929). If you upgrade from older instructions that referenced `5001` or another port, update your Docker Compose or `docker run` mapping accordingly.

## Q: What is `--once` / one-shot mode?
- `run.py --once` (or equivalent CLI) runs the processing loop once (a single scheduled job or work batch) and exits. It's useful for CI smoke-tests or cron-style invocation where you don't want an always-on container.

## Q: How do I run tests locally?
- Create a virtualenv, install dependencies and dev/test tools, then run pytest. Example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
python -m pytest -q
```

If you use the repository helpers or CI snippets, see `tests/commands/run_tests.yml` for a sample developer command.

## Q: Where are the health and metrics endpoints?
- researcharr exposes `/health` and `/metrics` on port `2929` for use in Docker healthchecks and monitoring. See `docs/Health-and-Metrics.md` for examples and recommended Docker healthcheck configuration.

## Q: Where are the plugin docs and examples?
- The repository contains a `researcharr/plugins` package with an example and the plugin contract. See `docs/` and `README.md` for high-level info. If you plan to write or install third-party plugins, see the `docs/` notes and consider using the plugin registry system (planned/implemented depending on your branch).

## Q: I still see references to the old wiki — is that intended?
- The project has migrated most docs into the `docs/` folder in this repository. If you find stale links that point to the wiki, please open an issue or submit a PR — the docs have been updated in most places to reference local `docs/` files.

## Q: Need more help
- If this FAQ doesn't answer your question, open a GitHub issue or ask on the discussion for the repo. Include logs and the output of `docker logs` or `python -m pytest` as relevant.

````
