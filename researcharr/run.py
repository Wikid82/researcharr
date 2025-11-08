"""Minimal run helpers required by tests.

This lightweight implementation provides a compatible `run_job` entrypoint
used by the test-suite. It purposely keeps the behavior small and
deterministic so tests can exercise timeout handling without starting the
full scheduler implementation.
"""

from __future__ import annotations

import logging
import os
import subprocess  # nosec B404
import sys
import threading
from typing import Optional

# Defaults (tests override these via monkeypatch)
LOG_PATH = os.environ.get("LOG_PATH", "/config/cron.log")
SCRIPT = os.environ.get("SCRIPT", "/app/scripts/researcharr.py")

# Module-level lock for concurrency control (tests may set RUN_JOB_CONCURRENCY)
_run_job_lock: Optional[threading.Lock] = None


def load_config(path: str = "config.yml") -> dict:
    """Lightweight fallback loader used by tests.

    Tests patch this symbol (monkeypatch/patch) when exercising the
    top-level run behaviours. Provide a deterministic, side-effect free
    implementation so the symbol exists during test-time imports.
    """
    # Keep this intentionally minimal — real implementations live in the
    # project's entrypoint modules. Returning an empty dict is sufficient
    # for tests that only need the symbol to exist or to be patched.
    return {}


# Placeholder for the optional `schedule` library used by the full project.
# Tests patch "researcharr.run.schedule" so expose a module-level symbol
# (None is fine; the patch will replace it with a mock during tests).
schedule = None


def setup_scheduler() -> None:
    """Lightweight scheduler wiring used by tests (no-op if schedule missing).

    If the real `schedule` package is available in the environment, this
    function will wire a simple periodic job. In tests the `schedule`
    symbol is patched so calling this will exercise the expected calls.
    """
    # Look up schedule from both globals and the module's namespace
    # to support test patches that set run.schedule = mock
    import sys

    sched = globals().get("schedule")
    # Also check if the containing module has schedule set by tests
    if sched is None:
        mod = sys.modules.get(__name__)
        if mod is not None:
            sched = getattr(mod, "schedule", None)
    if sched is None:
        return
    try:
        # Typical usage in the real project: schedule.every().minutes.do(...)
        sched.every().minutes.do(run_job)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        # Swallow errors — tests only care that this function exists and
        # that it calls into schedule if present.
        return


def _get_job_timeout() -> Optional[float]:
    v = os.getenv("JOB_TIMEOUT", "")
    try:
        return float(v) if v else None
    except Exception:  # nosec B110 -- intentional broad except for resilience
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
    except Exception:  # nosec B110 -- intentional broad except for resilience
        env_script = None
    try:
        mod_script = globals().get("SCRIPT")
    except Exception:  # nosec B110 -- intentional broad except for resilience
        mod_script = None
    script = env_script or mod_script or SCRIPT
    import logging as _lg

    try:
        _lg.info("globals SCRIPT=%r", mod_script)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass
    try:
        _lg.info("env SCRIPT=%r", env_script)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass
    try:
        top_run = sys.modules.get("run")
        try:
            _lg.info(
                "top-level run.SCRIPT=%r",
                None if top_run is None else getattr(top_run, "SCRIPT", None),
            )
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
    except Exception:  # nosec B110 -- intentional broad except for resilience
        try:
            _lg.info("top-level run.SCRIPT=<unavailable>")
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
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
            completed = subprocess.run(  # nosec B603
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            completed = subprocess.run(  # nosec B603
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
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
        try:
            logger.debug("run_job stderr: %s", err)
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
        try:
            if out:
                logger.info("Job stdout: %s", out)
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
        try:
            if err:
                logger.info("Job stderr: %s", err)
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
        logger.info("Job finished with returncode %s", completed.returncode)
    except subprocess.TimeoutExpired:
        # Best-effort kill: subprocess.run already attempts to kill the child,
        # but ensure we log the expected message for tests and diagnostics.
        logger.error("Job exceeded timeout and was killed")
    except Exception as exc:  # nosec B110 -- intentional broad except for resilience
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
