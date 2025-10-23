#!/usr/bin/env python3
"""Run the Flask web UI and an in-process scheduler to replace system cron.

This file starts the Flask app (from `factory.create_app`) and an
APScheduler BackgroundScheduler that invokes the existing
`/app/researcharr.py` script on the configured cron schedule. Logs from
scheduled runs are written to `/config/cron.log`.
"""
import os
import sys
import yaml
import logging
import subprocess
import importlib.util
import sys

# Ensure the `researcharr` package directory is loaded as a package name so
# imports like `from researcharr import webui` resolve to the package in
# /app/researcharr instead of the top-level /app/researcharr.py script
# which would otherwise shadow the package.
pkg_init = "/app/researcharr/__init__.py"
if os.path.exists(pkg_init):
    spec = importlib.util.spec_from_file_location(
        "researcharr", pkg_init, submodule_search_locations=["/app/researcharr"]
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["researcharr"] = pkg
    spec.loader.exec_module(pkg)

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from factory import create_app

CONFIG_PATH = "/config/config.yml"
LOG_PATH = "/config/cron.log"
SCRIPT = "/app/researcharr.py"


def setup_logger():
    logger = logging.getLogger("researcharr.cron")
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers when reloading in tests
    if not logger.handlers:
        fh = logging.FileHandler(LOG_PATH)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.propagate = False
    return logger


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        logger = logging.getLogger("researcharr.cron")
        logger.exception("Failed to parse config file %s", CONFIG_PATH)
        return {}


def run_job():
    logger = logging.getLogger("researcharr.cron")
    logger.info("Starting scheduled job: running %s", SCRIPT)
    try:
        res = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        if res.stdout:
            logger.info("Job stdout:\n%s", res.stdout.strip())
        if res.stderr:
            logger.error("Job stderr:\n%s", res.stderr.strip())
        logger.info("Job finished with returncode %s", res.returncode)
    except Exception:
        logger.exception("Scheduled job failed to execute")


def main():
    # Ensure log file exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    open(LOG_PATH, "a").close()

    setup_logger()
    logger = logging.getLogger("researcharr.cron")

    # Create the Flask application
    app = create_app()

    cfg = load_config()
    cron_schedule = None
    if isinstance(cfg, dict):
        cron_schedule = cfg.get("researcharr", {}).get("cron_schedule")

    if not cron_schedule:
        cron_schedule = "0 * * * *"

    # Start scheduler
    scheduler = BackgroundScheduler()
    try:
        try:
            trigger = CronTrigger.from_crontab(cron_schedule)
        except Exception:
            logger.exception("Invalid cron schedule '%s', falling back to hourly", cron_schedule)
            trigger = CronTrigger.from_crontab("0 * * * *")

        scheduler.add_job(run_job, trigger, id="researcharr_job", replace_existing=True)
        scheduler.start()

        # Run the job once at startup to preserve previous behaviour
        run_job()

        # Run the Flask app in the foreground so Docker PID 1 stays alive
        app.run(host="0.0.0.0", port=2929, threaded=True)

    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


if __name__ == "__main__":
    main()
