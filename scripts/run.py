#!/usr/bin/env python3
"""Run the Flask web UI and an in-process scheduler.

Starts the Flask app (from `factory.create_app`) and an
APScheduler BackgroundScheduler that invokes `/app/scripts/researcharr.py` on a
cron schedule. Scheduled runs log to `/config/cron.log`.
"""

import argparse
import importlib
import importlib.util

# stdlib imports grouped at top to satisfy flake8 E402
import logging
import os
import threading
from types import ModuleType
from typing import Any

import yaml

# Declare the temporary names with a loose Any|None so static analysis
# allows assigning None when the optional import fails. Use importlib to
# load the module to avoid binding a precise Callable type to these names
# and then assigning None in an except branch (which would trigger
# incompatible-assignment errors when a stub provides a strict signature).
_create_backup_file: Any | None = None
_prune_backups: Any | None = None
try:
    import importlib as _importlib

    _backups_mod = _importlib.import_module("researcharr.backups")
    _create_backup_file = getattr(_backups_mod, "create_backup_file", None)
    _prune_backups = getattr(_backups_mod, "prune_backups", None)
except Exception:
    _create_backup_file = None
    _prune_backups = None

# Declare the public module-level names with loose Any so callers and
# static analysis know they may be callables or None depending on
# availability of the shared helpers.
create_backup_file: Any | None = _create_backup_file
prune_backups: Any | None = _prune_backups
# (imports consolidated at file top)

# `resource` is a platform-specific stdlib module (POSIX). Annotate a
# temporary name as optional before attempting the import so mypy knows
# it may be None in non-POSIX environments.
_resource: ModuleType | None = None
try:
    import resource as _resource  # type: ignore
except Exception:
    _resource = None

resource: ModuleType | None = _resource

# Module-level lock used for run_job concurrency control. Declare here so
# static analyzers know the name exists.
_run_job_lock: threading.Lock | None = None


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
            def from_crontab(*_args, **_kwargs):
                return object()

        class _BackgroundScheduler:
            def __init__(self, timezone=None):
                self._jobs = []

            def add_job(self, func, trigger, **_kwargs):
                self._jobs.append((func, trigger))

            def start(self):
                return

            def shutdown(self, *_args, **_kwargs):
                return

        return _BackgroundScheduler, _CronTrigger


BackgroundScheduler, CronTrigger = _load_scheduler_classes()

WEBUI_SCRIPT = "/app/webui.py"
CONFIG_PATH = "/config/config.yml"
LOG_PATH = "/config/cron.log"
SCRIPT = "/app/scripts/researcharr.py"


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
        logger.exception("Failed to load config.yml")
        return {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    print("Placeholder run.py moved to scripts/")
