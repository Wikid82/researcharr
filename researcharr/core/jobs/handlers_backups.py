"""Job handlers for backup operations.

Provides asynchronous handlers that wrap the existing synchronous backup
implementation functions so they can execute inside the job queue.

Handlers use the following naming convention:
    - backup.create      (create a new backup, optional prefix)
    - backup.prune       (prune backups according to config)
    - backup.restore     (restore an existing backup)
    - backup.validate    (validate a backup file)

The handlers are intentionally lightweight wrappers around the existing
functions in ``researcharr.backups_impl`` to avoid duplication and keep
behavior consistent with current API endpoints.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from .types import JobDefinition

# Import backing implementation helpers directly for deterministic behavior.
from ...backups_impl import (
    create_backup_file,
    prune_backups,
    restore_backup as impl_restore_backup,
    validate_backup_file,
)


async def backup_create(job: JobDefinition, progress):  # noqa: D401 - concise handler
    """Create a backup archive.

    kwargs:
        prefix: Optional filename prefix
    """
    config_root = os.getenv("CONFIG_DIR", "/config")
    backups_dir = os.path.join(config_root, "backups")
    prefix = job.kwargs.get("prefix", "") or ""

    await progress(0, 4, "Preparing backup environment")
    Path(backups_dir).mkdir(parents=True, exist_ok=True)

    await progress(1, 4, "Creating backup archive")
    name = await asyncio.to_thread(create_backup_file, config_root, backups_dir, prefix)

    await progress(2, 4, "Pruning old backups")
    # Load pruning config from environment or default – mirrors existing logic.
    try:
        retain_count = int(os.getenv("BACKUP_RETAIN_COUNT", "10"))
        retain_days = int(os.getenv("BACKUP_RETAIN_DAYS", "30"))
        cfg = {"retain_count": retain_count, "retain_days": retain_days}
        await asyncio.to_thread(prune_backups, backups_dir, cfg)
    except Exception:
        pass

    await progress(3, 4, "Finalizing")
    result_name = None
    if name:
        try:
            result_name = os.path.basename(str(name))
        except Exception:
            result_name = str(name)

    await progress(4, 4, "Backup complete")
    return {"backup_name": result_name}


async def backup_prune(job: JobDefinition, progress):
    """Prune backups according to provided config.

    kwargs may include retain_count, retain_days.
    """
    config_root = os.getenv("CONFIG_DIR", "/config")
    backups_dir = os.path.join(config_root, "backups")
    cfg = {
        "retain_count": job.kwargs.get("retain_count"),
        "retain_days": job.kwargs.get("retain_days"),
        "pre_restore_keep_days": job.kwargs.get("pre_restore_keep_days"),
    }
    await progress(0, 2, "Pruning backups")
    await asyncio.to_thread(prune_backups, backups_dir, cfg)
    await progress(2, 2, "Prune complete")
    return {"pruned": True}


async def backup_restore(job: JobDefinition, progress):
    """Restore a backup archive.

    args:
        - backup filename (str)
    kwargs:
        pre_backup_prefix: Optional prefix for pre-restore snapshot (default 'pre-')
        create_pre_backup: bool (default True)
    """
    if not job.args:
        raise ValueError("backup filename is required")
    backup_name = str(job.args[0])
    config_root = os.getenv("CONFIG_DIR", "/config")
    backups_dir = os.path.join(config_root, "backups")
    backup_path = os.path.join(backups_dir, backup_name)
    create_pre = bool(job.kwargs.get("create_pre_backup", True))
    pre_prefix = str(job.kwargs.get("pre_backup_prefix", "pre-"))

    await progress(0, 5, "Validating backup path")
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_name}")

    if create_pre:
        await progress(1, 5, "Creating pre-restore backup")
        try:
            await asyncio.to_thread(create_backup_file, config_root, backups_dir, pre_prefix)
            await asyncio.to_thread(prune_backups, backups_dir, {"retain_count": int(os.getenv("BACKUP_RETAIN_COUNT", "10"))})
        except Exception:
            pass
    else:
        await progress(1, 5, "Skipping pre-restore snapshot")

    await progress(2, 5, "Restoring backup archive")
    restore_ok = await asyncio.to_thread(impl_restore_backup, backup_path, config_root)
    if not restore_ok:
        raise RuntimeError("Restore failed")

    await progress(3, 5, "Post-restore cleanup")
    # No-op placeholder; future: verify integrity or restart services.

    await progress(5, 5, "Restore complete")
    return {"restored": True, "backup_name": backup_name}


async def backup_validate(job: JobDefinition, progress):
    """Validate a backup file is a proper zip archive."""
    if not job.args:
        raise ValueError("backup filename is required")
    backup_name = str(job.args[0])
    config_root = os.getenv("CONFIG_DIR", "/config")
    backups_dir = os.path.join(config_root, "backups")
    backup_path = os.path.join(backups_dir, backup_name)
    await progress(0, 1, "Validating")
    valid = await asyncio.to_thread(validate_backup_file, backup_path)
    await progress(1, 1, "Validation complete")
    return {"valid": bool(valid)}


def register_backup_handlers(job_service: Any) -> None:
    """Register all backup handlers with the provided job service.

    The service is expected to expose a ``register_handler`` method.
    """
    if not job_service:
        return None
    try:
        job_service.register_handler("backup.create", backup_create)
        job_service.register_handler("backup.prune", backup_prune)
        job_service.register_handler("backup.restore", backup_restore)
        job_service.register_handler("backup.validate", backup_validate)
    except Exception:
        # Intentionally swallow to avoid breaking application startup.
        pass

__all__ = [
    "backup_create",
    "backup_prune",
    "backup_restore",
    "backup_validate",
    "register_backup_handlers",
]
