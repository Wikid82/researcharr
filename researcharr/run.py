"""Minimal run helpers required by tests.

This lightweight implementation provides a compatible `run_job` entrypoint
used by the test-suite. It purposely keeps the behavior small and
deterministic so tests can exercise timeout handling without starting the
full scheduler implementation.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from typing import Optional

# Defaults (tests override these via monkeypatch)
LOG_PATH = os.environ.get("LOG_PATH", "/config/cron.log")
SCRIPT = os.environ.get("SCRIPT", "/app/scripts/researcharr.py")

# Module-level lock for concurrency control (tests may set RUN_JOB_CONCURRENCY)
_run_job_lock: Optional[threading.Lock] = None


def _get_job_timeout() -> Optional[float]:
    v = os.getenv("JOB_TIMEOUT", "")
    try:
        return float(v) if v else None
    except Exception:
        return None


def run_job() -> None:
    """Run the configured SCRIPT and enforce JOB_TIMEOUT if set.

    Logs to the `researcharr.cron` logger so tests can capture messages with
    caplog.
    """
    logger = logging.getLogger("researcharr.cron")

    # Resolve the script path dynamically so callers can override it by
    # setting the module attribute on either the package module or the
    # top-level `run` module (some import paths may alias one to the
    # other in different environments).
    # Prefer an explicit environment override (tests set this). Fall back to
    # the module-level attribute, then to the package default constant.
    try:
        env_script = os.environ.get("SCRIPT")
    except Exception:
        env_script = None
    try:
        mod_script = globals().get("SCRIPT")
    except Exception:
        mod_script = None
    script = env_script or mod_script or SCRIPT
    logger.debug("globals SCRIPT=%r", mod_script)
    logger.debug("env SCRIPT=%r", env_script)
    try:
        top_run = sys.modules.get("run")
        logger.debug(
            "top-level run.SCRIPT=%r",
            None if top_run is None else getattr(top_run, "SCRIPT", None),
        )
    except Exception:
        logger.debug("top-level run.SCRIPT=<unavailable>")
    timeout = _get_job_timeout()

    # Ensure there is something to execute
    if not script:
        logger.error("No SCRIPT configured for run_job")
        return

    logger.debug("selected script for run_job: %s", script)
    logger.info("Starting scheduled job: running %s", script)

    try:
        # Use subprocess.run which raises TimeoutExpired if the child exceeds
        # the specified timeout. This tends to be simpler and more reliable
        # than managing Popen.communicate/timeouts manually.
        # Call subprocess.run with explicit keyword arguments. Using a
        # dynamically-built `run_kwargs` dict can confuse static type
        # checkers (Pyright/Pylance) which may try to match the dict values
        # to positional parameters and report spurious type errors. By
        # providing the keywords directly we avoid that issue and keep the
        # runtime behavior the same.
        if timeout is not None:
            completed = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            completed = subprocess.run(
                [sys.executable, str(script)], capture_output=True, text=True
            )
        out = completed.stdout
        err = completed.stderr
        # Log subprocess output for diagnostic visibility in tests.
        # Log at DEBUG normally, but if the child returned a non-zero exit
        # status surface its stdout/stderr at INFO so tests (which set INFO)
        # can capture diagnostic traces.
        try:
            # Always provide the child's output at DEBUG; tests look for the
            # more human-facing "Job stdout" / "Job stderr" lines at INFO.
            logger.debug("run_job stdout: %s", out)
        except Exception:
            pass
        try:
            logger.debug("run_job stderr: %s", err)
        except Exception:
            pass
        try:
            if out:
                logger.info("Job stdout: %s", out)
        except Exception:
            pass
        try:
            if err:
                logger.info("Job stderr: %s", err)
        except Exception:
            pass
        logger.info("Job finished with returncode %s", completed.returncode)
    except subprocess.TimeoutExpired:
        # Best-effort kill: subprocess.run already attempts to kill the child,
        # but ensure we log the expected message for tests and diagnostics.
        logger.error("Job exceeded timeout and was killed")
    except Exception as exc:
        logger.exception("run_job encountered an error: %s", exc)


def main(once: bool = False) -> None:
    """Simple main entry matching the project contract (not used by tests)."""
    if once:
        run_job()
    else:
        # In the real project this would start the scheduler loop. Keep it
        # minimal here for tests and local usage.
        while True:
            run_job()
            break
