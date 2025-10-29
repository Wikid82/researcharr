"""Compatibility shim for backups.

Expose create_backup_file and prune_backups under the package namespace
`researcharr.backups` by delegating to the top-level module `backups`.
This keeps runtime imports working regardless of whether the project is
installed as a package or run from the repository root.
"""

from __future__ import annotations

try:
    from backups import create_backup_file, prune_backups  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    # Provide helpful error functions if delegation fails
    def create_backup_file(*_args, **_kwargs):
        raise ImportError("Could not import top-level backups module")

    def prune_backups(*_args, **_kwargs):
        raise ImportError("Could not import top-level backups module")
