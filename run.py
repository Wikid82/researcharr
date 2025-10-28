#!/usr/bin/env python3
"""Run the Flask web UI and an in-process scheduler.

Starts the Flask app (from `factory.create_app`) and an
APScheduler BackgroundScheduler that invokes `/app/researcharr.py` on a
cron schedule. Scheduled runs log to `/config/cron.log`.
"""
import argparse
import importlib
import importlib.util
import logging
import os
import subprocess
import sys
import threading
from types import ModuleType

import yaml

try:
    # Prefer importing the shared helpers from the package
    from researcharr.backups import create_backup_file, prune_backups
except Exception:
    create_backup_file = None
    prune_backups = None
import json
import time

# `resource` is a platform-specific stdlib module (POSIX). Annotate a
# temporary name as optional before attempting the import so mypy knows
# it may be None in non-POSIX environments.
_resource: ModuleType | None = None
try:
    import resource as _resource  # type: ignore
except Exception:
    _resource = None

resource: ModuleType | None = _resource


def _load_scheduler_classes():
    """Load APScheduler classes or provide fallbacks."""
    try:
        sched_name = "apscheduler.schedulers.background"
        cron_name = "apscheduler.triggers.cron"
        sched_mod = importlib.import_module(sched_name)
        cron_mod = importlib.import_module(cron_name)
        return sched_mod.BackgroundScheduler, cron_mod.CronTrigger
    except Exception:

        class _CronTrigger:
            @staticmethod
            def from_crontab(expr, timezone=None):
                return object()

        class _BackgroundScheduler:
            def __init__(self, timezone=None):
                self._jobs = []

            def add_job(self, func, trigger, id=None, replace_existing=False):
                self._jobs.append((func, trigger))

            def start(self):
                return

            def shutdown(self, wait=False):
                return

        return _BackgroundScheduler, _CronTrigger


BackgroundScheduler, CronTrigger = _load_scheduler_classes()

WEBUI_SCRIPT = "/app/webui.py"
CONFIG_PATH = "/config/config.yml"
LOG_PATH = "/config/cron.log"
SCRIPT = "/app/researcharr.py"


def setup_logger():
    logger = logging.getLogger("researcharr.cron")
    logger.setLevel(logging.INFO)

    def _add_file_handler():
        fh = logging.FileHandler(LOG_PATH)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.propagate = False

    if not logger.handlers:
        _add_file_handler()
    else:
        try:
            first = logger.handlers[0]
            current = getattr(first, "baseFilename", None)
        except Exception:
            current = None
        if current != LOG_PATH:
            for h in list(logger.handlers):
                try:
                    logger.removeHandler(h)
                except Exception:
                    pass
            _add_file_handler()
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
    """Run scheduled job with timeout and optional RLIMITs."""
    logger = logging.getLogger("researcharr.cron")
    start_ts = time.time()

    global _run_job_lock
    try:
        _run_job_lock
    except NameError:
        _run_job_lock = threading.Lock()

    concurrency = int(os.getenv("RUN_JOB_CONCURRENCY", "1"))
    if concurrency <= 1:
        acquired = _run_job_lock.acquire(blocking=False)
        if not acquired:
            logger.info("Previous job still running; skipping run")
            return

    try:
        logger.info("Starting scheduled job: running %s", SCRIPT)

        rlimit_as_mb = os.getenv("JOB_RLIMIT_AS_MB")
        rlimit_cpu = os.getenv("JOB_RLIMIT_CPU_SECONDS")

        preexec = None
        if resource is not None and (rlimit_as_mb or rlimit_cpu):
            if rlimit_as_mb:
                try:
                    as_bytes = int(rlimit_as_mb) * 1024 * 1024
                except Exception:
                    as_bytes = None
            else:
                as_bytes = None

            if rlimit_cpu:
                try:
                    cpu_seconds = int(rlimit_cpu)
                except Exception:
                    cpu_seconds = None
            else:
                cpu_seconds = None

            def _limit_resources():
                try:
                    if as_bytes is not None:
                        as_limit = (as_bytes, as_bytes)
                        resource.setrlimit(resource.RLIMIT_AS, as_limit)
                    if cpu_seconds is not None:
                        cpu_limit = (cpu_seconds, cpu_seconds)
                        resource.setrlimit(resource.RLIMIT_CPU, cpu_limit)
                except Exception:
                    pass

            preexec = _limit_resources

        try:
            timeout_val = int(os.getenv("JOB_TIMEOUT", "0"))
            timeout_arg = timeout_val if timeout_val > 0 else None
        except Exception:
            timeout_arg = None

        try:
            # Build kwargs only with keys supported/needed.
            # Tests may monkeypatch the subprocess module with a simple
            # object that doesn't accept
            # `timeout` or `preexec_fn`.
            run_kwargs = {"capture_output": True, "text": True}
            if timeout_arg is not None:
                run_kwargs["timeout"] = timeout_arg
            if preexec is not None:
                run_kwargs["preexec_fn"] = preexec

            res = subprocess.run([sys.executable, SCRIPT], **run_kwargs)
            if res.stdout:
                logger.info("Job stdout:\n%s", res.stdout.strip())
            if res.stderr:
                logger.error("Job stderr:\n%s", res.stderr.strip())
            logger.info("Job finished with returncode %s", res.returncode)
            # Persist a structured run record to JSONL for reliable history
            try:
                config_dir = os.getenv("CONFIG_DIR", "/config")
                hist_file = os.path.join(config_dir, "task_history.jsonl")
                rec = {
                    "start_ts": int(start_ts),
                    "start_iso": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_ts)
                    ),
                    "returncode": int(getattr(res, "returncode", -1)),
                    "stdout": res.stdout or "",
                    "stderr": res.stderr or "",
                    "duration_seconds": round(time.time() - start_ts, 2),
                    "success": getattr(res, "returncode", 1) == 0,
                }
                try:
                    os.makedirs(config_dir, exist_ok=True)
                    with open(hist_file, "a") as hf:
                        hf.write(json.dumps(rec) + "\n")
                except Exception:
                    logger.exception("Failed to write task history to %s", hist_file)
            except Exception:
                pass
        except getattr(subprocess, "TimeoutExpired", Exception):
            logger.error("Scheduled job exceeded timeout and was killed")
        except Exception:
            logger.exception("Scheduled job failed to execute")
    finally:
        if concurrency <= 1:
            try:
                _run_job_lock.release()
            except Exception:
                pass

            pass


def main(once: bool = False):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    open(LOG_PATH, "a").close()

    setup_logger()
    logger = logging.getLogger("researcharr.cron")

    try:
        ver_path = os.getenv("RESEARCHARR_VERSION_FILE", "/app/VERSION")
        if os.path.exists(ver_path):
            info = {}
            with open(ver_path) as vf:
                for line in vf.read().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
            logger.info("Image build info: %s", info)
            try:
                print(f"[run.py] Image build info: {info}")
                sys.stdout.flush()
            except Exception:
                pass
    except Exception:
        logger.exception("Failed to read /app/VERSION for build info")

    cfg = load_config()
    cron_schedule = None
    if isinstance(cfg, dict):
        cron_schedule = cfg.get("researcharr", {}).get("cron_schedule")

    if not cron_schedule:
        cron_schedule = "0 * * * *"

    scheduler = BackgroundScheduler(timezone="UTC")
    try:
        try:
            trigger = CronTrigger.from_crontab(cron_schedule, timezone="UTC")
        except Exception:
            logger.exception("Invalid cron schedule; falling back to hourly")
            logger.debug("Bad cron schedule: %s", cron_schedule)
            trigger = CronTrigger.from_crontab("0 * * * *", timezone="UTC")

        scheduler.add_job(
            run_job,
            trigger,
            id="researcharr_job",
            replace_existing=True,
        )

        # backup helpers and scheduled prune/auto-backup
        def _read_backups_cfg():
            config_dir = os.getenv("CONFIG_DIR", "/config")
            cfg_file = os.path.join(config_dir, "backups.yml")
            defaults = {
                "retain_count": 10,
                "retain_days": 30,
                "pre_restore": True,
                "pre_restore_keep_days": 1,
                "auto_backup_enabled": False,
                "auto_backup_cron": "0 2 * * *",
                "prune_cron": "0 3 * * *",
            }
            try:
                if os.path.exists(cfg_file):
                    with open(cfg_file) as fh:
                        data = yaml.safe_load(fh) or {}
                    defaults.update(data)
            except Exception:
                logger.exception("Failed to read backups config %s", cfg_file)
            return defaults

        # If the shared helpers are available, use them; otherwise fall back
        # to no-op implementations so the scheduler can still start in tests
        # where the package import path may differ.
        def _create_backup_file_run(prefix: str = ""):
            if create_backup_file is None:
                logger.debug("create_backup_file helper not available")
                return None
            config_dir = os.getenv("CONFIG_DIR", "/config")
            backups_dir = os.path.join(config_dir, "backups")
            return create_backup_file(config_dir, backups_dir, prefix=prefix)

        def _prune_backups_run():
            if prune_backups is None:
                logger.debug("prune_backups helper not available")
                return
            cfg = _read_backups_cfg()
            config_dir = os.getenv("CONFIG_DIR", "/config")
            backups_dir = os.path.join(config_dir, "backups")
            prune_backups(backups_dir, cfg)

        try:
            bcfg = _read_backups_cfg()
            # Prune job
            prune_cron = bcfg.get("prune_cron")
            if prune_cron:
                try:
                    ptrigger = CronTrigger.from_crontab(prune_cron, timezone="UTC")
                    scheduler.add_job(
                        _prune_backups_run,
                        ptrigger,
                        id="prune_backups",
                        replace_existing=True,
                    )
                except Exception:
                    logger.exception("Invalid prune cron: %s", prune_cron)
            # Auto backup
            if bcfg.get("auto_backup_enabled"):
                ab_cron = bcfg.get("auto_backup_cron") or "0 2 * * *"
                try:
                    abtrigger = CronTrigger.from_crontab(ab_cron, timezone="UTC")

                    def _auto_backup_wrapper():
                        name = _create_backup_file_run()
                        if name:
                            logger.info("Auto-backup created %s", name)
                            # prune after creating
                            try:
                                _prune_backups_run()
                            except Exception:
                                logger.exception("Prune after auto-backup failed")

                    scheduler.add_job(
                        _auto_backup_wrapper,
                        abtrigger,
                        id="auto_backup",
                        replace_existing=True,
                    )
                except Exception:
                    logger.exception("Invalid auto backup cron: %s", ab_cron)
        except Exception:
            logger.exception("Failed to schedule backup/prune jobs")
        scheduler.start()

        run_job()

        if once:
            logger.info("One-shot mode: exiting after running job once")
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass
            return

        try:
            spec = importlib.util.spec_from_file_location(
                "factory_mod", "/app/factory.py"
            )
            if spec is None or spec.loader is None:
                logger.error("Failed to create ModuleSpec for factory.py")
                return
            factory_mod = importlib.util.module_from_spec(spec)
            loader = spec.loader
            assert loader is not None
            loader.exec_module(factory_mod)
            app = factory_mod.create_app()
            port_env = os.getenv("WEBUI_PORT")
            try:
                port = int(port_env) if port_env else 2929
            except Exception:
                port = 2929

            print(f"[run.py] Starting Flask app on port {port}...")
            sys.stdout.flush()
            app.run(host="0.0.0.0", port=port, threaded=True)
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
    parser = argparse.ArgumentParser(
        description=("Run researcharr web UI and scheduler")
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run scheduled job once and exit (no web UI)",
    )
    args = parser.parse_args()
    main(once=args.once)
