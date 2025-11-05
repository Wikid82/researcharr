"""Compatibility shim for backups.

Expose create_backup_file and prune_backups under the package namespace
`researcharr.backups` by delegating to the top-level module `backups`.
This keeps runtime imports working regardless of whether the project is
installed as a package or run from the repository root.
"""

from __future__ import annotations

import os


def _delegate_to_top_level(name: str, *args, **kwargs):
    """Attempt to delegate a call to the top-level backups module.

    We import on-demand here instead of at module import time so that code
    which installs the package (or runs tests) doesn't get a brittle
    import-time failure when the repo layout / sys.path differs between
    environments (CI vs editable installs vs running from source).
    """
    try:
        # import inside function to pick up top-level `backups.py` when
        # the caller's sys.path includes the repository root.
        from backups import cleanup_temp_files as _ctf
        from backups import create_backup_file as _cb  # type: ignore
        from backups import get_backup_info as _gbi
        from backups import get_backup_size as _gbs
        from backups import get_default_backup_config as _gdbc
        from backups import list_backups as _lb
        from backups import merge_backup_configs as _mbc
        from backups import prune_backups as _pb
        from backups import restore_backup as _rb
        from backups import validate_backup_file as _vbf
    except Exception:
        # If a normal import fails (for example because the current working
        # directory is the configured CONFIG_DIR during tests), try to load
        # the repository's top-level `backups.py` by path relative to this
        # package. This makes the delegation robust regardless of CWD.
        try:
            import importlib.util

            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            candidate = os.path.join(repo_root, "backups.py")
            spec = importlib.util.spec_from_file_location("backups", candidate)
            if spec is None or spec.loader is None:
                raise ImportError("failed to load backups.py from repository")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            _cb = getattr(mod, "create_backup_file")
            _pb = getattr(mod, "prune_backups")
            _gbi = getattr(mod, "get_backup_info")
            _lb = getattr(mod, "list_backups")
            _rb = getattr(mod, "restore_backup")
            _vbf = getattr(mod, "validate_backup_file")
            _gbs = getattr(mod, "get_backup_size")
            _ctf = getattr(mod, "cleanup_temp_files")
            _gdbc = getattr(mod, "get_default_backup_config")
            _mbc = getattr(mod, "merge_backup_configs")
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ImportError("Could not import top-level backups module") from exc

    if name == "create_backup_file":
        return _cb(*args, **kwargs)
    if name == "prune_backups":
        return _pb(*args, **kwargs)
    if name == "get_backup_info":
        return _gbi(*args, **kwargs)
    if name == "list_backups":
        return _lb(*args, **kwargs)
    if name == "restore_backup":
        return _rb(*args, **kwargs)
    if name == "validate_backup_file":
        return _vbf(*args, **kwargs)
    if name == "get_backup_size":
        return _gbs(*args, **kwargs)
    if name == "cleanup_temp_files":
        return _ctf(*args, **kwargs)
    if name == "get_default_backup_config":
        return _gdbc(*args, **kwargs)
    if name == "merge_backup_configs":
        return _mbc(*args, **kwargs)


def create_backup_file(*args, **kwargs):
    return _delegate_to_top_level("create_backup_file", *args, **kwargs)


def prune_backups(*args, **kwargs):
    return _delegate_to_top_level("prune_backups", *args, **kwargs)


def get_backup_info(*args, **kwargs):
    return _delegate_to_top_level("get_backup_info", *args, **kwargs)


def list_backups(*args, **kwargs):
    return _delegate_to_top_level("list_backups", *args, **kwargs)


def restore_backup(*args, **kwargs):
    return _delegate_to_top_level("restore_backup", *args, **kwargs)


def validate_backup_file(*args, **kwargs):
    return _delegate_to_top_level("validate_backup_file", *args, **kwargs)


def get_backup_size(*args, **kwargs):
    return _delegate_to_top_level("get_backup_size", *args, **kwargs)


def cleanup_temp_files(*args, **kwargs):
    return _delegate_to_top_level("cleanup_temp_files", *args, **kwargs)


def get_default_backup_config(*args, **kwargs):
    return _delegate_to_top_level("get_default_backup_config", *args, **kwargs)


def merge_backup_configs(*args, **kwargs):
    return _delegate_to_top_level("merge_backup_configs", *args, **kwargs)
