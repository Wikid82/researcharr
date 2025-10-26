"""Compatibility package shim.

This project historically exposes a top-level module layout (e.g. factory.py,
researcharr.py, plugins/*). Tests and some consumers import `researcharr.*`.

To allow `import researcharr.plugins` and `import researcharr.factory` without
restructuring the repository, this package provides lightweight shims that
redirect imports to the existing top-level modules and plugins directory.
"""

# Expose a minimal package namespace; individual submodules are provided as
# small wrapper modules under the same package.

import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional

__all__ = []


# Candidate locations for the implementation module. We check the current
# working directory first (test runners often run from the repo root), then
# fall back to paths relative to this package directory.
TOP_LEVEL: Optional[str] = None
# Try several candidate locations where the implementation may live. Tests and
# different run contexts may execute with different working directories, so
# include both cwd-based and package-relative locations.
candidates = [
    os.path.join(os.getcwd(), "researcharr.py"),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr.py")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "researcharr.py")),
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "researcharr.py")
    ),
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "researcharr",
            "researcharr.py",
        )
    ),
]
for c in candidates:
    if os.path.isfile(c):
        TOP_LEVEL = c
        break
# If not found yet, walk up a few directory levels from the package dir to
# look for a top-level `researcharr.py`. This covers several CI/test layouts.
if not TOP_LEVEL:
    base = os.path.dirname(__file__)
    for depth in range(1, 6):
        candidate = os.path.abspath(
            os.path.join(base, *([".."] * depth), "researcharr.py")
        )
        if os.path.isfile(candidate):
            TOP_LEVEL = candidate
            break


# Prefer a deterministic, file-based loader for the implementation module.
# Locate the top-level `researcharr.py` file first (several plausible
# locations) and load it by path. Falling back to package import-style is
# fragile under pytest's import ordering, so prefer the explicit path loader.
researcharr: Optional[ModuleType] = None
impl_candidates = [
    os.path.join(os.getcwd(), "researcharr.py"),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "researcharr.py")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr.py")),
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "researcharr.py")
    ),
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "researcharr", "researcharr.py")
    ),
]
for c in impl_candidates:
    if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(__file__):
        TOP_LEVEL = c
        break

if TOP_LEVEL:
    spec = importlib.util.spec_from_file_location("researcharr.researcharr", TOP_LEVEL)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]

        # Expose commonly-patched top-level names on the loaded module
        from typing import Optional as _Optional

        _requests: _Optional[ModuleType] = None
        _req: _Optional[ModuleType] = None
        try:
            import requests as _req_import  # type: ignore

            _req = _req_import
        except Exception:
            _req = None
        if _req is not None:
            _requests = _req

        _yaml: _Optional[ModuleType] = None
        _y: _Optional[ModuleType] = None
        try:
            import yaml as _y_import  # type: ignore

            _y = _y_import
        except Exception:
            _y = None
        if _y is not None:
            _yaml = _y

        if _requests is not None and not hasattr(mod, "requests"):
            setattr(mod, "requests", _requests)
        if _yaml is not None and not hasattr(mod, "yaml"):
            setattr(mod, "yaml", _yaml)

        # Register the implementation under the canonical package name and
        # attach it to the package namespace so tests can import it
        # deterministically.
        sys.modules["researcharr.researcharr"] = mod
        researcharr = mod
        __all__ = ["researcharr"]
        # Also set attribute on the package module object itself.
        try:
            setattr(sys.modules[__name__], "researcharr", mod)
        except Exception:
            pass
else:
    # Fallback: attempt package-style import if no implementation file found.
    try:
        import importlib

        researcharr = importlib.import_module("researcharr.researcharr")
        if not (
            hasattr(researcharr, "init_db")
            or hasattr(researcharr, "create_metrics_app")
        ):
            researcharr = None
        else:
            __all__ = ["researcharr"]
    except Exception:
        researcharr = None
