"""Package shim to ensure `from researcharr import researcharr` returns
the real implementation module object.

Some runners and test harnesses import the package in different ways which
can cause multiple module objects to be created for the implementation.
This loader tries a normal import first and validates the imported module
contains expected implementation symbols. If validation fails it will
load the top-level ``researcharr.py`` by path and insert the loaded module
into ``sys.modules`` under the name ``researcharr.researcharr`` and set
the attribute on the package module so all import forms resolve to the
same implementation object.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional


def _is_impl_module(mod: ModuleType) -> bool:
    """Return True if the module looks like the real implementation.

    We check for a couple of names the test-suite and application expect to
    be present. If the names are missing we treat the module as a shim and
    attempt file-based loading instead.
    """
    return any(
        hasattr(mod, name)
        for name in (
            "init_db",
            "create_metrics_app",
            "check_radarr_connection",
        )
    )


def _load_by_path(candidates: list[str]) -> Optional[ModuleType]:
    for path in candidates:
        if not path:
            continue
        if os.path.isfile(path):
            try:
                spec = importlib.util.spec_from_file_location(
                    "researcharr.researcharr", path
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    # Execute module in its own namespace
                    spec.loader.exec_module(mod)  # type: ignore[arg-type]
                    # Some loaders may not set __file__; ensure it's present so
                    # consumers that inspect __file__ get a meaningful path.
                    try:
                        if not hasattr(mod, "__file__") or not getattr(mod, "__file__"):
                            setattr(mod, "__file__", os.path.abspath(path))
                    except Exception:
                        pass
                    return mod
            except Exception:
                # Loading by path is best-effort here; fall through to try
                # other candidates.
                continue
    return None


# First, try the normal import path which works when the package is
# installed or when imports resolve to the expected module.
impl: Optional[ModuleType] = None
try:
    impl = importlib.import_module("researcharr.researcharr")
    if not _is_impl_module(impl):
        impl = None
except Exception:
    impl = None

if impl is None:
    # Build candidate paths where a top-level `researcharr.py` might live.
    base = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        os.path.join(os.getcwd(), "researcharr.py"),
        os.path.join(base, "researcharr.py"),
        os.path.abspath(os.path.join(base, "..", "researcharr.py")),
        os.path.abspath(os.path.join(base, "..", "..", "researcharr.py")),
    ]
    impl = _load_by_path(candidates)

if impl:
    # Preserve a small set of attributes which may have been set on an
    # existing module object (for example by test fixtures using
    # monkeypatch.setattr("researcharr.researcharr.<name>", ...)). If a
    # previous module exists, copy over common test-patched names so tests
    # that set attributes prior to reload/import continue to work.
    existing = sys.modules.get("researcharr.researcharr")
    if existing is not None:
        for attr in (
            "setup_logger",
            "main_logger",
            "radarr_logger",
            "sonarr_logger",
            "DB_PATH",
            "USER_CONFIG_PATH",
        ):
            if not hasattr(impl, attr) and hasattr(existing, attr):
                try:
                    setattr(impl, attr, getattr(existing, attr))
                except Exception:
                    pass

    # Register the implementation under the expected module name and set
    # the package attribute so all import forms resolve to the same
    # implementation object.
    sys.modules["researcharr.researcharr"] = impl
    pkg = sys.modules.get("researcharr")
    if pkg is not None:
        try:
            setattr(pkg, "researcharr", impl)
        except Exception:
            # Non-fatal: best-effort to set the attribute for consumers.
            pass


# Expose a convenience name for debugging/import inspection
__all__ = ["researcharr"]
