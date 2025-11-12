"""Package shim that exposes the repository-top `plugins` package as
`researcharr.plugins` for editor/static-analysis friendliness.

At runtime we attempt to import the top-level `plugins` package and
re-export its public names. This keeps behavior consistent whether the
project is used from a source checkout or as an installed package.
"""

from __future__ import annotations

import importlib
from typing import Any

# Predefine exported names so static analysis sees them even when the
# runtime import can't run inside the type checker/editor environment.
registry: Any = None
base: Any = None
clients: Any = None
media: Any = None
notifications: Any = None
scrapers: Any = None

_impl: Any | None = None
try:
    # Prefer the repository-level `plugins` package when present.
    _impl = importlib.import_module("plugins")
except Exception:
    _impl = None

if _impl is not None:
    # Re-export commonly used symbols. Keep this explicit to help static
    # tooling and ensure the names exist in this module even when the
    # underlying implementation isn't present during static analysis.
    for _name in (
        "registry",
        "base",
        "clients",
        "media",
        "notifications",
        "scrapers",
    ):
        try:
            val: Any = getattr(_impl, _name, None)
            globals()[_name] = val
        except Exception:
            globals()[_name] = None

__all__ = [
    "registry",
    "base",
    "clients",
    "media",
    "notifications",
    "scrapers",
]
