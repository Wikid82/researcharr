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

# Public convenience name required by some tooling/tests. Will be assigned to
# the implementation module object when it is discovered below.
researcharr: Optional[ModuleType] = None


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
    # If file-based loading did not produce an implementation, try a normal
    # import of the submodule name. In some import orders Python will be
    # able to locate the package submodule even when the direct file-based
    # loader path didn't run or failed earlier.
    if impl is None:
        try:
            maybe = importlib.import_module("researcharr.researcharr")
            if _is_impl_module(maybe):
                impl = maybe
        except Exception:
            pass

if impl:
    # Ensure the implementation module has a usable __file__ value. Some
    # import mechanisms or test harnesses may produce modules where
    # __file__ is unset; prefer the module spec's origin when available
    # otherwise leave any existing value untouched.
    try:
        if not getattr(impl, "__file__", None):
            spec = getattr(impl, "__spec__", None)
            origin = getattr(spec, "origin", None) if spec is not None else None
            if origin:
                try:
                    setattr(impl, "__file__", os.path.abspath(origin))
                except Exception:
                    pass
            # As a fallback, try to find the spec by name which in some
            # environments will provide a reliable origin path.
            if not getattr(impl, "__file__", None):
                try:
                    spec2 = importlib.util.find_spec("researcharr.researcharr")
                    if spec2 is not None:
                        origin2 = getattr(spec2, "origin", None)
                    else:
                        origin2 = None
                    if origin2:
                        setattr(impl, "__file__", os.path.abspath(origin2))
                except Exception:
                    pass
    except Exception:
        pass
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
    # Prefer an explicit load of the package-level implementation file
    # (researcharr/researcharr.py) when present. This ensures a consistent
    # implementation module object regardless of import order or how the
    # import machinery resolved the package name earlier.
    try:
        base = os.path.abspath(os.path.dirname(__file__))
        pkg_impl_path = os.path.join(base, "researcharr", "researcharr.py")
        if os.path.isfile(pkg_impl_path):
            # Only reload if the current impl doesn't already come from
            # that path.
            if os.path.abspath(getattr(impl, "__file__", "")) != os.path.abspath(
                pkg_impl_path
            ):
                name = "researcharr.researcharr"
                spec = importlib.util.spec_from_file_location(name, pkg_impl_path)
                if spec and spec.loader:
                    new_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(new_mod)  # type: ignore[arg-type]
                    impl = new_mod
    except Exception:
        # Non-fatal: fall back to previously-determined impl if anything
        # goes wrong while trying to prefer the package file.
        pass
    if impl is not None:
        sys.modules["researcharr.researcharr"] = impl
        pkg = sys.modules.get("researcharr")
        if pkg is not None:
            try:
                setattr(pkg, "researcharr", impl)
            except Exception:
                # Non-fatal: best-effort to set the attribute for consumers.
                pass
    # Ensure common dependent modules are available as attributes on the
    # implementation and registered in sys.modules. This makes dotted
    # import paths (used by tests and monkeypatch) resolve correctly.
    try:
        # Annotate these names so mypy knows they may be None on some
        # platforms/environments where the optional dependencies are missing.
        _requests_module: ModuleType | None = None
        _yaml_module: ModuleType | None = None
        try:
            import requests as _requests_module  # type: ignore[assignment]
        except Exception:
            _requests_module = None
        try:
            import yaml as _yaml_module  # type: ignore[assignment]
        except Exception:
            _yaml_module = None

        if _requests_module is not None and not getattr(impl, "requests", None):
            try:
                setattr(impl, "requests", _requests_module)
                name = "researcharr.researcharr.requests"
                sys.modules.setdefault(name, _requests_module)
            except Exception:
                pass

        if _yaml_module is not None and not getattr(impl, "yaml", None):
            try:
                setattr(impl, "yaml", _yaml_module)
                name = "researcharr.researcharr.yaml"
                sys.modules.setdefault(name, _yaml_module)
            except Exception:
                pass
    except Exception:
        pass


# Expose a convenience name for debugging/import inspection
__all__ = ["researcharr"]

# Export the discovered implementation module under the convenient name
# so tools and editors that consult module globals see the symbol.
try:
    if "impl" in globals() and impl is not None:
        researcharr = impl
except Exception:
    pass
