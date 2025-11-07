"""Package-level proxy for the repo-root `factory.py` module.

This shim imports the top-level `factory` implementation (at the repo
root) and re-exports its public names so editors and static analysis can
resolve `researcharr.factory` as a real module inside the package.
"""

from __future__ import annotations

import importlib
from typing import Any  # noqa: F401

try:
    _impl = importlib.import_module("factory")
except Exception:
    _impl = None  # type: ignore[assignment]

# Always expose the `_impl` symbol on the shim module so tests that
# reload `researcharr.factory` may end up operating against the top-level
# module object depending on import order; having `_impl` present makes
# the shim/import-failure test deterministic.
globals()["_impl"] = _impl

if _impl is not None:
    # Ensure the repo-level module object is treated as the canonical
    # implementation under both import names. This makes import-time
    # identity consistent so tests that patch `researcharr.factory` or
    # the top-level `factory` observe the same module object.
    try:
        import sys as _sys

        # Force the well-known import names to refer to the repo-level
        # implementation module object. Using direct assignment avoids
        # leaving duplicate module objects under different keys which
        # breaks tests that patch one of those names.
        try:
            _sys.modules["factory"] = _impl
        except Exception:
            # best-effort; ignore failures to overwrite mapping
            pass
        try:
            _sys.modules["researcharr.factory"] = _impl
        except Exception:
            pass
    except Exception:
        # best-effort; don't fail import on sys.modules manipulation
        pass

    # Re-export public names from the implementation for static analysis
    # and backwards compatibility.
    globals().update(
        {name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")}
    )
    # Do not compute __all__ dynamically here; some editors (Pylance)
    # warn about operations on __all__. The shim re-exports all public
    # names via globals().update above which is sufficient for static
    # analysis and runtime import resolution.
