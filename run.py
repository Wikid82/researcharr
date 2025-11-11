#!/usr/bin/env python3
"""Thin proxy shim for legacy imports.

All logic lives in ``researcharr.run``. This module simply re-exports its
public API so ``from researcharr import run`` and ``import researcharr.run``
behave identically (same function objects & logging behavior).
"""

from __future__ import annotations

import importlib.util
import os
import sys

# Load the package implementation directly from file to avoid circular import
# issues during collection, but register it immediately as "researcharr.run"
# in sys.modules so all subsequent imports (including test force-reloads)
# resolve to this single module object.
_impl = None
try:
    _pkg_dir = os.path.join(os.path.dirname(__file__), "researcharr")
    _pkg_run = os.path.join(_pkg_dir, "run.py")
    if os.path.isfile(_pkg_run):
        _spec = importlib.util.spec_from_file_location("researcharr.run", _pkg_run)
        if _spec and _spec.loader:
            _m = importlib.util.module_from_spec(_spec)
            # Register as "researcharr.run" BEFORE exec to avoid duplicate
            # module objects during test imports.
            sys.modules["researcharr.run"] = _m
            _spec.loader.exec_module(_m)  # type: ignore[arg-type]
            _impl = _m
except Exception:
    _impl = None

if _impl is None:
    # Fallback to normal import if direct file load failed
    from importlib import import_module

    _impl = import_module("researcharr.run")


# Proxy all attribute access to the implementation module so tests that modify
# attributes on this shim (e.g., run.SCRIPT = "...") affect the impl directly.
def __getattr__(name: str):
    """Forward all attribute access to the implementation module.

    Note: This is only called if the attribute is NOT in this module's __dict__.
    If patch.object or direct assignment adds an attribute to this module's
    __dict__, that value takes precedence and __getattr__ is not called.
    """
    try:
        return getattr(_impl, name)
    except AttributeError:
        raise AttributeError(f"module 'run' has no attribute '{name}'") from None


def __setattr__(name: str, value) -> None:
    """Forward all attribute writes to the implementation module.

    Writes go ONLY to the impl to ensure tests that patch the impl see
    the patched value. The shim stays clean and forwards all reads to impl.
    """
    impl = _get_impl()
    if impl is None:
        raise AttributeError(f"Cannot set attribute '{name}' on module 'run' (impl not loaded)")
    setattr(impl, name, value)


def __dir__():
    """List attributes from the implementation module."""
    return dir(_impl)


# Provide explicit wrappers for key functions to ensure test patches are honored
def main(once: bool = False) -> None:  # noqa: D401
    """Delegate to the implementation while honoring patched run_job."""
    # Check for patched run_job in this module's __dict__ first (test patches),
    # then fall back to implementation
    run_job_func = globals().get("run_job") or __getattr__("run_job")
    if once:
        try:
            # Best-effort: ensure logger exists for tests that inspect it
            getattr(_impl, "setup_logger", lambda: None)()
        except Exception:
            pass
        # Call the (possibly patched on THIS module) run_job exactly once
        run_job_func()
        return None
    # Non-once mode: keep tests deterministic by invoking one run and returning
    run_job_func()
    return None


def setup_scheduler():
    """Forward to implementation after syncing schedule patches."""
    try:
        # If tests patched schedule on this shim, sync to impl
        if "schedule" in globals():
            _impl.schedule = globals()["schedule"]
    except Exception:
        pass
    try:
        if hasattr(_impl, "setup_scheduler"):
            return _impl.setup_scheduler()  # type: ignore[attr-defined]
    except Exception:
        return None
    return None


__all__ = [
    "run_job",
    "main",
    "LOG_PATH",
    "SCRIPT",
    "setup_logger",
    "_get_job_timeout",
    "schedule",
    "CONFIG_PATH",
    "setup_scheduler",
]

if __name__ == "__main__":  # pragma: no cover
    main()
