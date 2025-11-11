"""Backwards-compatible thin shim for top-level `backups`.

The canonical implementation lives in `researcharr.backups_impl`. This
file provides a minimal, explicit re-export so tests and consumers that
import the top-level `backups` module get the same public functions.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_IMPL: Any | None = None
try:
    # Import the concrete implementations from the package internals.
    # The canonical, full implementation lives in `researcharr.backups_impl`.
    # Bind the top-level shim to that implementation to preserve historical
    # behavior for legacy imports and tests.
    _IMPL = import_module("researcharr.backups_impl")
    # Pull attributes from the implementation module if present; fall back to safe defaults
    BackupPath = getattr(_IMPL, "BackupPath", None)
    get_backup_info = getattr(_IMPL, "get_backup_info", lambda *a, **kw: None)
    prune_backups = getattr(_IMPL, "prune_backups", lambda *a, **kw: None)
    list_backups = getattr(_IMPL, "list_backups", lambda *a, **kw: [])
    restore_backup = getattr(_IMPL, "restore_backup", lambda *a, **kw: False)
    validate_backup_file = getattr(_IMPL, "validate_backup_file", lambda *a, **kw: False)
    get_backup_size = getattr(_IMPL, "get_backup_size", lambda *a, **kw: 0)
    cleanup_temp_files = getattr(_IMPL, "cleanup_temp_files", lambda *a, **kw: None)
    get_default_backup_config = getattr(_IMPL, "get_default_backup_config", lambda *a, **kw: {})
    merge_backup_configs = getattr(_IMPL, "merge_backup_configs", lambda *a, **kw: {})
except Exception:
    # Provide safe fallbacks so tests that inject a top-level module into
    # ``sys.modules`` can still run without the package implementation.
    BackupPath = None  # type: ignore

    def prune_backups(*a: Any, **kw: Any) -> Any:
        return None

    def get_backup_info(*a: Any, **kw: Any) -> Any:
        return None

    def list_backups(*a: Any, **kw: Any) -> list:
        return []

    def restore_backup(*a: Any, **kw: Any) -> bool:
        return False

    def validate_backup_file(*a: Any, **kw: Any) -> bool:
        return False

    def get_backup_size(*a: Any, **kw: Any) -> int:
        return 0

    def cleanup_temp_files(*a: Any, **kw: Any) -> None:
        return None

    def get_default_backup_config(*a: Any, **kw: Any) -> dict:
        return {}

    def merge_backup_configs(*a: Any, **kw: Any) -> dict:
        return {}


__all__ = [
    "BackupPath",
    "create_backup_file",
    "get_backup_info",
    "prune_backups",
    "get_backup_config",
]


def get_backup_config(config_root: str | Any) -> dict:
    """Return a minimal backup configuration mapping.

    Provides a "backups_dir" key pointing at ``<config_root>/backups`` and merges
    defaults when available. Tests monkeypatch this symbol; keep implementation
    intentionally simple.
    """
    try:
        from pathlib import Path
        import os as _os

        root = Path(str(config_root or _os.getenv("CONFIG_DIR", "/config")))
        backups_dir = root / "backups"
        defaults = {}
        try:
            defaults = get_default_backup_config()  # type: ignore[name-defined]
        except Exception:
            defaults = {}
        cfg = {"backups_dir": str(backups_dir)}
        try:
            # Merge defaults without overwriting backups_dir
            merged = dict(defaults)
            merged.update(cfg)
            return merged
        except Exception:
            return cfg
    except Exception:
        return {"backups_dir": f"{config_root}/backups"}

# Ensure package-qualified name points to the same module object
# Top-level shim should not override the package-qualified module mapping;
# leave package-level imports to resolve to `researcharr.backups` inside the
# package so tests and consumers observe the package API.


def create_backup_file(config_root, backups_dir, prefix=""):
    """Compatibility wrapper used by legacy top-level imports.

    Historically, the top-level `backups.create_backup_file` raised if the
    source `config_root` did not exist and no prefix was provided. Preserve
    that behavior while delegating the real work to
    ``researcharr.backups_impl.create_backup_file``.
    """
    from pathlib import Path

    cr = Path(config_root)
    if not cr.exists() and not prefix:
        raise Exception("config_root does not exist and no prefix provided")
    # Delegate to the implementation module
    if _IMPL is None:
        raise ImportError("backups_impl not available")
    return _IMPL.create_backup_file(config_root, backups_dir, prefix=prefix)


# Ensure a stable sys.modules mapping for reload friendliness when this
# module is imported under a package-qualified name (e.g.
# 'researcharr.backups'). Some import orders load this file via a
# spec with the package-qualified name; make sure that name points to
# this module object so importlib.reload() can find it.
try:
    import sys as _sys

    _sp = globals().get("__spec__", None)
    _nm = getattr(_sp, "name", None) or __name__
    _mod = _sys.modules.get(__name__)
    if _mod is not None and _nm:
        _sys.modules[_nm] = _mod
except Exception:
    pass
