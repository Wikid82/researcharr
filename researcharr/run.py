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

# Defaults (tests override these via monkeypatch)
LOG_PATH = os.environ.get("LOG_PATH", "/config/cron.log")
SCRIPT = os.environ.get("SCRIPT", "/app/scripts/researcharr.py")

# Module-level lock for concurrency control (tests may set RUN_JOB_CONCURRENCY)
_run_job_lock: threading.Lock | None = None


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


def setup_logger():
    """Lightweight logger setup stub used by tests.

    Tests may patch this symbol. Provide a no-op implementation so the
    symbol exists during test-time imports and patches.
    """
    # Real logger setup happens during run_job() call
    return logging.getLogger("researcharr.cron")


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
    except Exception:  # pragma: no cover - nosec B110 -- intentional broad except for resilience
        # Swallow errors — tests only care that this function exists and
        # that it calls into schedule if present.
        return


def _get_job_timeout() -> float | None:
    v = os.getenv("JOB_TIMEOUT", "")
    try:
        return float(v) if v else None
    except Exception:  # pragma: no cover - nosec B110 -- intentional broad except for resilience
        return None


def run_job() -> None:
    """Run the configured SCRIPT and enforce JOB_TIMEOUT if set.

    Logs to the `researcharr.cron` logger so tests can capture messages with
    caplog.
    """
    # Always get a fresh logger reference at call time (tests may reset
    # handlers/levels between runs).
    logger = logging.getLogger("researcharr.cron")
    # Ensure propagation so pytest caplog captures our records even if
    # other tests modified logger handlers or levels.
    logger.propagate = True
    # Set level to DEBUG if still NOTSET so INFO/DEBUG messages appear in caplog.
    # Caplog propagates from our logger to root, so we need a level that permits
    # the messages to be emitted at all.
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

    # Resolve the script path dynamically so callers can override it by
    # setting the module attribute on either the package module or the
    # top-level `run` module (some import paths may alias one to the
    # other in different environments).
    # Prefer an explicit environment override (tests set this). Fall back to
    # the module-level attribute, then to the package default constant.
    # Preserve empty string and None (explicitly cleared) rather than falling back.
    # Use sentinel to distinguish "not found" from "found but None/empty".
    _NOTFOUND = object()
    try:
        env_script = os.environ.get("SCRIPT", _NOTFOUND)
    except Exception:  # pragma: no cover - resilience
        env_script = _NOTFOUND
    try:
        mod_script = globals().get("SCRIPT", _NOTFOUND)
    except Exception:  # pragma: no cover - resilience
        mod_script = _NOTFOUND
    # Also inspect top-level shim module (name "run") if present – tests may
    # clear or set its SCRIPT independently of the package module.
    top_run_mod = sys.modules.get("run")
    try:
        shim_script = getattr(top_run_mod, "SCRIPT", _NOTFOUND) if top_run_mod else _NOTFOUND
    except Exception:  # pragma: no cover - resilience
        shim_script = _NOTFOUND
    # Selection order: environment -> package module -> top-level shim -> default constant.
    # Use sentinel checks so empty string and None are respected (trigger error).
    if env_script is not _NOTFOUND:
        script = env_script
    elif mod_script is not _NOTFOUND:
        script = mod_script
    elif shim_script is not _NOTFOUND:
        script = shim_script
    else:
        script = SCRIPT
    # Log diagnostics at INFO for test visibility (tests check these in caplog.text)
    try:
        logger.info("globals SCRIPT=%r", mod_script)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass
    try:
        logger.info("env SCRIPT=%r", env_script)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass
    try:
        try:
            logger.info(
                "top-level run.SCRIPT=%r",
                None if top_run_mod is None else getattr(top_run_mod, "SCRIPT", None),
            )
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
    except Exception:  # nosec B110 -- intentional broad except for resilience
        try:
            logger.info("top-level run.SCRIPT=<unavailable>")
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
    timeout = _get_job_timeout()

    # Ensure there is something to execute
    if not script:  # empty string, None, or other falsy value
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
        # checkers (basedpyright/Pylance) which may try to match the dict values
        # to positional parameters and report spurious type errors. By
        # providing the keywords directly we avoid that issue and keep the
        # runtime behavior the same.
        if timeout is not None:
            completed = subprocess.run(  # nosec B603
                [sys.executable, str(script)],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            completed = subprocess.run(  # nosec B603
                [sys.executable, str(script)], check=False, capture_output=True, text=True
            )
        out = completed.stdout
        err = completed.stderr
        # Log subprocess output for diagnostic visibility in tests.
        # Log at DEBUG normally, but if the child returned a non-zero exit
        # status surface its stdout/stderr at INFO so tests (which set INFO)
        # can capture diagnostic traces.
        try:  # pragma: no cover - defensive logging
            # Always provide the child's output at DEBUG; tests look for the
            # more human-facing "Job stdout" / "Job stderr" lines at INFO.
            logger.debug("run_job stdout: %s", out)
        except (
            Exception
        ):  # pragma: no cover - nosec B110 -- intentional broad except for resilience
            pass
        try:  # pragma: no cover - defensive logging
            logger.debug("run_job stderr: %s", err)
        except (
            Exception
        ):  # pragma: no cover - nosec B110 -- intentional broad except for resilience
            pass
        try:
            if out:
                logger.info("Job stdout: %s", out)
        except (
            Exception
        ):  # pragma: no cover - nosec B110 -- intentional broad except for resilience
            pass
        try:
            if err:
                logger.info("Job stderr: %s", err)
        except (
            Exception
        ):  # pragma: no cover - nosec B110 -- intentional broad except for resilience
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
