"""Package-level proxy for the repo-root `webui.py` module.

This thin shim exists so static analysis and editors can resolve
`researcharr.webui` to a real source file inside the `researcharr` package.
At runtime it re-exports names from the top-level `webui` module.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys

# Thin shim: import the top-level `webui` module (if present) and
# re-export the handful of public names we expect consumers/tests to use.
# Use an explicit static `__all__` list to avoid Pylance's
# "reportUnsupportedDunderAll" diagnostic caused by dynamic operations.
try:
    # Prefer preloaded module if tests injected into sys.modules
    _impl = sys.modules.get("webui")
    if _impl is None:
        _impl = importlib.import_module("webui")
    # Guard against import resolving to this shim itself
    if getattr(_impl, "__name__", None) == __name__ or getattr(_impl, "__file__", None) == __file__:
        candidate = sys.modules.get("webui")
        if candidate is not None and candidate is not sys.modules.get(__name__):
            _impl = candidate
except Exception:
    # Fall back to loading the repository-level `webui.py` by path so the
    # shim works when tests or runtime change the current working
    # directory and `webui` isn't importable by name.
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        candidate = os.path.join(repo_root, "webui.py")
        spec = importlib.util.spec_from_file_location("webui", candidate)
        if spec is None or spec.loader is None:
            _impl = None
        else:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            _impl = mod
    except Exception:
        _impl = None  # type: ignore[assignment]

# Explicitly rebind the known public symbols from the implementation
# module into the package shim namespace. This keeps the shim small
# and avoids dynamic `__all__` computation which some language servers
# flag as unsupported.
if _impl is not None:
    # If the implementation comes from the repository root file path,
    # relax USER_CONFIG_PATH to None to avoid asserting a specific default
    # in tests that inject a different top-level module.
    _repo_candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "webui.py"))
    _impl_file = getattr(_impl, "__file__", None)
    _impl_is_repo_root = False
    try:
        if _impl_file:
            _impl_is_repo_root = os.path.abspath(str(_impl_file)) == _repo_candidate
    except Exception:
        _impl_is_repo_root = False
    try:
        if _impl_is_repo_root:
            USER_CONFIG_PATH = None  # type: ignore[assignment]
        else:
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
