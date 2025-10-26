"""Wrapper so `researcharr.researcharr` points at the top-level
`researcharr.py` module.

This file loads the top-level ``researcharr.py`` by file path and inserts the
loaded module into ``sys.modules`` under the package name so imports and
``importlib.reload`` behave the same as when the project is installed.
"""

import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional

# Load the top-level `researcharr.py` module by file path to avoid importing
# this package (which would otherwise shadow the module name).
_mod: Optional[ModuleType] = None
# Exposed name for the loaded module (or None when not found).
module: Optional[ModuleType] = None

# Candidate locations for the top-level module. Different CI/test runners use
# different working directories, so search a number of plausible locations
# relative to both the current working directory and this shim file.
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
        ),
    ),
]

TOP_LEVEL = None
for c in candidates:
    if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(__file__):
        TOP_LEVEL = c
        break

# Fallback: walk upward a few levels from the package directory looking for
# a top-level `researcharr.py` file.
if not TOP_LEVEL:
    base = os.path.dirname(__file__)
    for depth in range(1, 6):
        candidate = os.path.abspath(
            os.path.join(base, *([".."] * depth), "researcharr.py")
        )
        if os.path.isfile(candidate) and os.path.abspath(candidate) != os.path.abspath(
            __file__
        ):
            TOP_LEVEL = candidate
            break

if TOP_LEVEL:
    # Use the package module name so importlib.reload and sys.modules
    # behave as callers expect (i.e. the module is known as
    # 'researcharr.researcharr').
    spec = importlib.util.spec_from_file_location(
        "researcharr.researcharr",
        TOP_LEVEL,
    )
    if spec and spec.loader:
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)  # type: ignore[arg-type]

if _mod:
    # Ensure commonly-patched top-level names exist on the loaded module so
    # tests that patch e.g. `researcharr.researcharr.requests` resolve
    # correctly even when the shim is used to load the implementation by
    # path.
    try:
        import requests as _requests  # type: ignore
    except Exception:
        _requests = None
    try:
        import yaml as _yaml  # type: ignore
    except Exception:
        _yaml = None

    if not hasattr(_mod, "requests") and _requests is not None:
        setattr(_mod, "requests", _requests)
    if not hasattr(_mod, "yaml") and _yaml is not None:
        setattr(_mod, "yaml", _yaml)

    # Replace this shim module in sys.modules with the loaded top-level
    # module so callers receive the real module object (functions will use
    # the correct globals and monkeypatching will work as expected).
    sys.modules[__name__] = _mod
    sys.modules["researcharr.researcharr"] = _mod

    # Also set the attribute on the parent package module (if present) so
    # `from researcharr import researcharr` resolves directly to the
    # implementation module in all import scenarios.
    parent = sys.modules.get("researcharr")
    if parent is not None:
        try:
            setattr(parent, "researcharr", _mod)
        except Exception:
            pass

    # Also expose the loaded module on the name 'module' for debugging
    module = _mod
else:
    module = None

# As a safety: if the loaded module appears to be missing expected public
# symbols (this can happen in some import-layout edge-cases), attempt to
# load the implementation directly and copy missing callables so tests and
# callers can access them from the package path.
if module is not None:
    for name in ("init_db", "create_metrics_app", "has_valid_url_and_key"):
        if not hasattr(module, name):
            try:
                spec2 = importlib.util.spec_from_file_location("researcharr_impl", TOP_LEVEL)
                if spec2 and spec2.loader:
                    impl = importlib.util.module_from_spec(spec2)
                    spec2.loader.exec_module(impl)  # type: ignore[arg-type]
                    if hasattr(impl, name):
                        setattr(module, name, getattr(impl, name))
            except Exception:
                # Don't fail tests just because the copy step couldn't run;
                # leave the attribute missing and let the test report it.
                pass
