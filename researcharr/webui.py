"""Package-level proxy for the repo-root `webui.py` module.

This thin shim exists so static analysis and editors can resolve
`researcharr.webui` to a real source file inside the `researcharr` package.
At runtime it re-exports names from the top-level `webui` module.
"""
from __future__ import annotations

import importlib

# Thin shim: import the top-level `webui` module (if present) and
# re-export the handful of public names we expect consumers/tests to use.
# Use an explicit static `__all__` list to avoid Pylance's
# "reportUnsupportedDunderAll" diagnostic caused by dynamic operations.
try:
    _impl = importlib.import_module("webui")
except Exception:
    _impl = None  # type: ignore[assignment]

# Explicitly rebind the known public symbols from the implementation
# module into the package shim namespace. This keeps the shim small
# and avoids dynamic `__all__` computation which some language servers
# flag as unsupported.
if _impl is not None:
    try:
        USER_CONFIG_PATH = getattr(_impl, "USER_CONFIG_PATH")
    except AttributeError:
        # Leave undefined when the implementation doesn't provide it.
        pass

    try:
        _env_bool = getattr(_impl, "_env_bool")
    except AttributeError:
        pass

    try:
        load_user_config = getattr(_impl, "load_user_config")
    except AttributeError:
        pass

    try:
        save_user_config = getattr(_impl, "save_user_config")
    except AttributeError:
        pass

# Static export list: keep this list small and explicit so editors can
# correctly determine the exported symbols without running code.
__all__ = [
    "USER_CONFIG_PATH",
    "_env_bool",
    "load_user_config",
    "save_user_config",
]
