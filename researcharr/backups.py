"""Package-level re-export shim for backups.

The implementation lives in ``researcharr._backups_impl``. Importing
``researcharr.backups`` will provide the same public API by re-exporting
symbols from the implementation module.
"""

from __future__ import annotations

from pathlib import Path

from . import backups_impl

# Re-export the stable, minimal helpers from the internal implementation
# module. We import specifically to keep the public surface explicit.
from ._backups_impl import BackupPath as _BackupPath

# Provide a stable public BackupPath for callers that expect the lightweight
# wrapper used in tests; prefer the internal _BackupPath if present but fall
# back to a simple Path-compatible alias.
try:
    BackupPath = _BackupPath  # type: ignore
except Exception:

    class BackupPath(str):
        def __new__(cls, fullpath: str, name: str):
            obj = str.__new__(cls, fullpath)
            object.__setattr__(obj, "_name", name)
            return obj

        def startswith(self, prefix: str) -> bool:  # type: ignore[override]
            try:
                import os as _os

                if prefix is None:
                    return False
                if prefix.startswith(_os.sep) or ("/" in prefix) or ("\\" in prefix):
                    return str(self).startswith(prefix)
                return str(object.__getattribute__(self, "_name")).startswith(prefix)
            except Exception:
                return str(self).startswith(prefix)


def create_backup_file(config_root, backups_dir, prefix: str = ""):
    # Preserve legacy behavior: if the config root does not exist and no
    # prefix was provided, treat this as an error (tests expect an
    # exception in that scenario). When a prefix is supplied we allow an
    # empty archive to be created instead.
    # Construct a Path for the config root; if Path() construction itself
    # fails we fall back to delegating to the implementation which will
    # raise a clearer error. Do NOT catch exceptions raised intentionally
    # below (for the missing config_root + empty prefix case) so tests
    # that expect an exception observe it.
    try:
        cfg = Path(config_root)
    except Exception:
        cfg = None

    if cfg is not None and not cfg.exists() and not prefix:
        # Preserve legacy behaviour: raise when the config root does not
        # exist and no prefix supplied.
        raise Exception(f"Config root does not exist: {config_root}")
    return backups_impl.create_backup_file(config_root, backups_dir, prefix=prefix)


def get_backup_info(*a, **kw):
    return backups_impl.get_backup_info(*a, **kw)


def prune_backups(*a, **kw):
    return backups_impl.prune_backups(*a, **kw)


def list_backups(*a, **kw):
    return backups_impl.list_backups(*a, **kw)


def restore_backup(*a, **kw):
    return backups_impl.restore_backup(*a, **kw)


def validate_backup_file(*a, **kw):
    return backups_impl.validate_backup_file(*a, **kw)


def get_backup_size(*a, **kw):
    return backups_impl.get_backup_size(*a, **kw)


def cleanup_temp_files(*a, **kw):
    return backups_impl.cleanup_temp_files(*a, **kw)


def get_default_backup_config(*a, **kw):
    return backups_impl.get_default_backup_config(*a, **kw)


def merge_backup_configs(*a, **kw):
    return backups_impl.merge_backup_configs(*a, **kw)


__all__ = [
    "BackupPath",
    "create_backup_file",
    "prune_backups",
    "get_backup_info",
    "list_backups",
    "restore_backup",
    "validate_backup_file",
    "get_backup_size",
    "cleanup_temp_files",
    "get_default_backup_config",
    "merge_backup_configs",
]
