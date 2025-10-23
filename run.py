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
import sys
import importlib.util
import argparse
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except Exception:
    # Provide lightweight fallbacks when APScheduler is not available
    # (useful for unit tests that don't install all runtime deps).
    class CronTrigger:
        @staticmethod
        def from_crontab(expr, timezone=None):
            return object()

    class BackgroundScheduler:
        def __init__(self, timezone=None):
            self._jobs = []

        def add_job(self, func, trigger, id=None, replace_existing=False):
            self._jobs.append((func, trigger))

        def start(self):
            return

        def shutdown(self, wait=False):
            return
import signal
import time

WEBUI_SCRIPT = "/app/webui.py"

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


def main(once: bool = False):
    # Ensure log file exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    open(LOG_PATH, "a").close()

    setup_logger()
    logger = logging.getLogger("researcharr.cron")

    cfg = load_config()
    cron_schedule = None
    if isinstance(cfg, dict):
        cron_schedule = cfg.get("researcharr", {}).get("cron_schedule")

    if not cron_schedule:
        cron_schedule = "0 * * * *"

    # Start scheduler (use UTC to avoid relying on system tzdata inside the
    # container; the web UI timezone setting can be honored later if desired)
    scheduler = BackgroundScheduler(timezone="UTC")
    try:
        try:
            trigger = CronTrigger.from_crontab(cron_schedule, timezone="UTC")
        except Exception:
            logger.exception("Invalid cron schedule '%s', falling back to hourly", cron_schedule)
            trigger = CronTrigger.from_crontab("0 * * * *", timezone="UTC")

        scheduler.add_job(run_job, trigger, id="researcharr_job", replace_existing=True)
        scheduler.start()

        # Run the job once at startup to preserve previous behaviour
        run_job()

        # If the user requested a one-shot run, exit after running the job
        if once:
            logger.info("One-shot mode: exiting after running scheduled job once")
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass
            return

        # Load the Flask app factory directly from /app/factory.py to avoid
        # import conflicts with the top-level `researcharr.py` module. We
        # load it as a separate module and call its create_app() function.
        try:
            spec = importlib.util.spec_from_file_location("factory_mod", "/app/factory.py")
            factory_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(factory_mod)
            app = factory_mod.create_app()
            # Run the Flask app in the foreground (this keeps PID 1 alive).
            print("[run.py] Starting Flask app...")
            sys.stdout.flush()
            app.run(host="0.0.0.0", port=2929, threaded=True)
            print("[run.py] Flask app terminated")
            sys.stdout.flush()
        except Exception:
            logger.exception("Failed to start web UI from factory.py")
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run researcharr web UI and scheduler")
    parser.add_argument("--once", action="store_true", help="Run scheduled job once and exit (no web UI)")
    args = parser.parse_args()
    main(once=args.once)
