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

if _impl is not None:
    globals().update(
        {name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")}
    )
    # Do not compute __all__ dynamically here; some editors (Pylance)
    # warn about operations on __all__. The shim re-exports all public
    # names via globals().update above which is sufficient for static
    # analysis and runtime import resolution.
