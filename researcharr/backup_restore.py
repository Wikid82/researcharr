"""Enhanced backup restoration with automatic rollback capabilities.

This module wraps the core restore_backup functionality with additional
safety mechanisms including pre-restore snapshots, integrity checking,
and automatic rollback on failure.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from researcharr.backups import restore_backup, validate_backup_file
from researcharr.compat import UTC
from researcharr.monitoring.backup_monitor import get_backup_monitor
from researcharr.storage.recovery import (
    check_db_integrity,
    get_alembic_head_revision,
    read_backup_meta,
    snapshot_sqlite,
    suggest_image_tag_from_meta,
)


class RestoreResult:
    """Result of a restore operation."""

    def __init__(
        self,
        success: bool,
        message: str,
        backup_path: str | Path,
        snapshot_path: str | Path | None = None,
        rollback_executed: bool = False,
        errors: list[str] | None = None,
    ):
        self.success = success
        self.message = message
        self.backup_path = Path(backup_path)
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self.rollback_executed = rollback_executed
        self.errors = errors or []

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "backup_path": str(self.backup_path),
            "snapshot_path": str(self.snapshot_path) if self.snapshot_path else None,
            "rollback_executed": self.rollback_executed,
            "errors": self.errors,
        }


def restore_with_rollback(
    backup_path: str | Path,
    config_dir: str | Path | None = None,
    auto_rollback: bool = True,
    cleanup_snapshot: bool = False,
    force: bool = False,
) -> RestoreResult:
    """Restore from backup with automatic rollback on failure.

    This function provides a safe restore operation that:
    1. Validates the backup before restoration
    2. Creates a pre-restore snapshot
    3. Performs the restore
    4. Verifies database integrity
    5. Automatically rolls back if integrity check fails (when auto_rollback=True)

    Args:
        backup_path: Path to backup file to restore
        config_dir: Configuration directory (default: $CONFIG_DIR or /config)
        auto_rollback: Automatically rollback on failure (default: True)
        cleanup_snapshot: Remove snapshot after successful restore (default: False)
        force: Skip schema version warnings (default: False)

    Returns:
        RestoreResult: Result object with success status and details
    """
    if config_dir is None:
        config_dir = Path(os.environ.get("CONFIG_DIR", "/config"))
    else:
        config_dir = Path(config_dir)

    backup_path = Path(backup_path)
    errors = []
    snapshot_path = None
    monitor = get_backup_monitor()

    # Validate backup exists
    if not backup_path.exists():
        return RestoreResult(
            success=False,
            message=f"Backup not found: {backup_path}",
            backup_path=backup_path,
            errors=["Backup file does not exist"],
        )

    # Validate backup integrity
    if not validate_backup_file(backup_path):
        monitor.record_backup_restored(backup_path, success=False)
        return RestoreResult(
            success=False,
            message="Backup validation failed",
            backup_path=backup_path,
            errors=["Backup file is corrupted or invalid"],
        )

    # Check schema compatibility
    meta = read_backup_meta(backup_path)
    if meta and not force:
        current_revision = get_alembic_head_revision()
        backup_revision = meta.get("alembic_revision")

        if current_revision and backup_revision and current_revision != backup_revision:
            warning = (
                f"Schema version mismatch: current={current_revision}, backup={backup_revision}"
            )
            errors.append(warning)

            suggested_tag = suggest_image_tag_from_meta(meta)
            if suggested_tag:
                errors.append(f"Consider using image: {suggested_tag}")

            # Allow proceeding but record the warning
            if not force:
                return RestoreResult(
                    success=False,
                    message="Schema version mismatch (use force=True to override)",
                    backup_path=backup_path,
                    errors=errors,
                )

    # Create pre-restore snapshot
    db_path = config_dir / "researcharr.db"
    if db_path.exists():
        backups_dir = config_dir / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        snapshot_path = backups_dir / f"pre-restore-{timestamp}.db"

        if not snapshot_sqlite(db_path, snapshot_path):
            monitor.record_backup_restored(backup_path, success=False)
            return RestoreResult(
                success=False,
                message="Failed to create pre-restore snapshot",
                backup_path=backup_path,
                errors=["Could not create safety snapshot before restore"],
            )

        monitor.record_pre_restore_snapshot(snapshot_path)

    # Perform restore
    try:
        restore_success = restore_backup(backup_path, config_dir)
        if not restore_success:
            if snapshot_path and auto_rollback:
                # Attempt rollback
                if snapshot_sqlite(snapshot_path, db_path):
                    monitor.record_backup_restored(backup_path, success=False, rollback=True)
                    return RestoreResult(
                        success=False,
                        message="Restore failed, automatic rollback executed",
                        backup_path=backup_path,
                        snapshot_path=snapshot_path,
                        rollback_executed=True,
                        errors=[
                            "Restore operation failed",
                            "Database rolled back to pre-restore state",
                        ],
                    )
                else:
                    monitor.record_backup_restored(backup_path, success=False)
                    return RestoreResult(
                        success=False,
                        message="Restore and rollback both failed",
                        backup_path=backup_path,
                        snapshot_path=snapshot_path,
                        errors=[
                            "Restore failed",
                            "Rollback also failed",
                            f"Manual recovery needed from: {snapshot_path}",
                        ],
                    )
            else:
                monitor.record_backup_restored(backup_path, success=False)
                return RestoreResult(
                    success=False,
                    message="Restore failed",
                    backup_path=backup_path,
                    snapshot_path=snapshot_path,
                    errors=[f"Pre-restore snapshot available at: {snapshot_path}"],
                )

    except Exception as e:  # nosec B110
        if snapshot_path and auto_rollback:
            # Attempt rollback on exception
            if snapshot_sqlite(snapshot_path, db_path):
                monitor.record_backup_restored(backup_path, success=False, rollback=True)
                return RestoreResult(
                    success=False,
                    message=f"Restore exception: {e}, automatic rollback executed",
                    backup_path=backup_path,
                    snapshot_path=snapshot_path,
                    rollback_executed=True,
                    errors=[
                        f"Exception during restore: {e}",
                        "Database rolled back to pre-restore state",
                    ],
                )

        monitor.record_backup_restored(backup_path, success=False)
        return RestoreResult(
            success=False,
            message=f"Restore exception: {e}",
            backup_path=backup_path,
            snapshot_path=snapshot_path,
            errors=[str(e)],
        )

    # Verify database integrity after restore
    if db_path.exists():
        if not check_db_integrity(db_path):
            if snapshot_path and auto_rollback:
                # Rollback due to integrity failure
                if snapshot_sqlite(snapshot_path, db_path):
                    monitor.record_backup_restored(backup_path, success=False, rollback=True)
                    return RestoreResult(
                        success=False,
                        message="Database integrity check failed, automatic rollback executed",
                        backup_path=backup_path,
                        snapshot_path=snapshot_path,
                        rollback_executed=True,
                        errors=[
                            "Restored database failed integrity check",
                            "Rolled back to pre-restore state",
                        ],
                    )
                else:
                    monitor.record_backup_restored(backup_path, success=False)
                    return RestoreResult(
                        success=False,
                        message="Integrity check failed, rollback also failed",
                        backup_path=backup_path,
                        snapshot_path=snapshot_path,
                        errors=[
                            "Database integrity check failed",
                            "Rollback failed",
                            f"Manual recovery needed from: {snapshot_path}",
                        ],
                    )
            else:
                monitor.record_backup_restored(backup_path, success=False)
                return RestoreResult(
                    success=False,
                    message="Database integrity check failed",
                    backup_path=backup_path,
                    snapshot_path=snapshot_path,
                    errors=[
                        "Restored database failed integrity check",
                        f"Snapshot available at: {snapshot_path}",
                    ],
                )

    # Success! Clean up snapshot if requested
    if snapshot_path and cleanup_snapshot and snapshot_path.exists():
        try:
            snapshot_path.unlink()
        except Exception:  # nosec B110
            pass  # Don't fail restore if cleanup fails

    monitor.record_backup_restored(backup_path, success=True)
    return RestoreResult(
        success=True,
        message="Restore completed successfully",
        backup_path=backup_path,
        snapshot_path=snapshot_path if not cleanup_snapshot else None,
    )
