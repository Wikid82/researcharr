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
    script = None
    try:
        script = globals().get("SCRIPT")
    except Exception:
        script = None
    logger.debug("globals SCRIPT=%r", globals().get("SCRIPT"))
    logger.debug("env SCRIPT=%r", os.environ.get("SCRIPT"))
    if not script:
        # Try top-level run module if present
        try:
            import sys
            run_mod = sys.modules.get("run")
            if run_mod is not None:
                script = getattr(run_mod, "SCRIPT", None)
        except Exception:
            pass
    logger.debug("top-level run.SCRIPT=%r", None if not __import__("sys").modules.get("run") else __import__("sys").modules.get("run").__dict__.get("SCRIPT"))
    if not script:
        # Fallback to environment
        script = os.environ.get("SCRIPT", SCRIPT)
    timeout = _get_job_timeout()

    # Ensure there is something to execute
    if not script:
        logger.error("No SCRIPT configured for run_job")
        return

    logger.debug("selected script for run_job: %s", script)

    try:
        # Launch the script as a subprocess and wait with optional timeout
        proc = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = proc.communicate(timeout=timeout)
            # Log subprocess output for diagnostic visibility in tests
            try:
                logger.debug("run_job stdout: %s", out.decode(errors="ignore"))
            except Exception:
                pass
            try:
                logger.debug("run_job stderr: %s", err.decode(errors="ignore"))
            except Exception:
                pass
            logger.info("run_job finished: %s", proc.returncode)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
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
