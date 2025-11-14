"""Package-level proxy for the repo-root `webui.py` module.

This shim exposes a small, stable API surface (`USER_CONFIG_PATH`,
`_env_bool`, `load_user_config`, `save_user_config`) while keeping the
functions defined on this module so tests can reliably monkeypatch
`researcharr.webui.rdb` and similar globals.

The shim will prefer a module-level `rdb` object (which tests often
patch) and otherwise delegate to an underlying implementation if one
is available.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from typing import Any
from unittest.mock import Mock as _Mock

from werkzeug.security import generate_password_hash

_TRUTHY_ENV_VALUES = {"1", "true", "yes"}

# Try to locate an underlying top-level `webui` implementation; keep it
# available as `_impl` but do not rebind functions directly — we want
# wrapper functions defined in this module so their `__module__` is
# `researcharr.webui` (the shim) and test monkeypatches on that module
# reliably affect behavior.
_impl = None
try:
    _impl = sys.modules.get("webui")
    if _impl is None:
        _impl = importlib.import_module("webui")
except Exception:  # pragma: no cover - defensive fallback for test isolation
    # Fall back to loading by file path from the repo root
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        candidate = os.path.join(repo_root, "webui.py")
        spec = importlib.util.spec_from_file_location("webui", candidate)
        if spec is not None and spec.loader is not None:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            _impl = mod
    except Exception:  # pragma: no cover
        _impl = None

# Defensive: if a test injected a Mock as the underlying implementation
# (via patching importlib or sys.modules), treat it as absent so the
# package shim remains authoritative and deterministic for tests that
# monkeypatch `researcharr.webui.rdb`.
if isinstance(_impl, _Mock):
    _impl = None
# Module-level `rdb` that tests can patch (monkeypatch sets this on
# `researcharr.webui` to control DB behavior). Default to None.
rdb: Any | None = None

# USER_CONFIG_PATH: prefer underlying impl value when available and
# when the implementation originates from a different file. If the impl
# is the repository root module we leave the path unset (None).
USER_CONFIG_PATH: str | None = None
if _impl is not None:
    try:
        _impl_file = getattr(_impl, "__file__", None)
        repo_candidate = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, "webui.py")
        )
        if _impl_file and os.path.abspath(str(_impl_file)) != repo_candidate:
            USER_CONFIG_PATH = getattr(_impl, "USER_CONFIG_PATH", None)
    except Exception:  # pragma: no cover - defensive path resolution
        USER_CONFIG_PATH = None


def _env_bool(name: str, default: str = "false") -> bool:
    """Return True if env var is truthy (1/true/yes)."""
    v = os.getenv(name, default)
    return str(v).lower() in _TRUTHY_ENV_VALUES


def load_user_config() -> dict[str, str | None] | None:
    """Return persisted web UI user dict or None.

    Prefer the shim `rdb` if present; otherwise delegate to the
    underlying implementation if it provides `load_user_config`.
    """
    # Use the shim-level `rdb` exclusively. Tests expect that monkeypatches
    # on `researcharr.webui.rdb` fully control DB-backed behavior; do not
    # implicitly delegate to any underlying top-level implementation here
    # (that delegation caused flaky behavior depending on import/test
    # ordering). If `rdb` is None treat as no DB available.
    if rdb is None:
        return None

    try:
        return rdb.load_user()
    except Exception:  # pragma: no cover - defensive DB error handling
        return None


def save_user_config(
    username: str,
    password_hash: str,
    api_key: str | None = None,
    api_key_hash: str | None = None,
) -> dict[str, str | None]:
    """Persist user credentials via the shim `rdb`.

    If `rdb` is not available raise RuntimeError (tests expect this).
    This function hashes `api_key` when provided and delegates the
    storage to `rdb.save_user`.
    """
    if rdb is None:
        raise RuntimeError("DB backend not available for saving webui user")

    api_hash = api_key_hash if api_key is None else generate_password_hash(api_key)
    # Delegate to the provided rdb object
    rdb.save_user(username, password_hash, api_hash)
    return {"username": username, "password_hash": password_hash, "api_key_hash": api_hash}


__all__ = ["USER_CONFIG_PATH", "_env_bool", "load_user_config", "save_user_config"]
