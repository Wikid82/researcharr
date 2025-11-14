"""Backup health monitoring and alerting system.

Monitors backup operations, tracks metrics, and publishes events for
alerting when backups fail or become stale.
"""
# basedpyright: reportArgumentType=false
# basedpyright: reportCallIssue=false

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from researcharr.backups import get_backup_info, list_backups
from researcharr.compat import UTC
from researcharr.core.events import get_event_bus
from researcharr.core.logging import get_logger

logger = get_logger(__name__)


class BackupEvents:
    """Event constants for backup operations."""

    BACKUP_CREATED = "backup.created"
    BACKUP_FAILED = "backup.failed"
    BACKUP_RESTORED = "backup.restored"
    BACKUP_RESTORE_FAILED = "backup.restore_failed"
    BACKUP_PRUNED = "backup.pruned"
    BACKUP_STALE = "backup.stale"
    BACKUP_VALIDATION_FAILED = "backup.validation_failed"
    PRE_RESTORE_SNAPSHOT_CREATED = "backup.pre_restore_snapshot_created"
    RESTORE_ROLLBACK_EXECUTED = "backup.restore_rollback_executed"


class BackupHealthMonitor:
    """Monitor backup health and publish alerts."""

    def __init__(
        self,
        config_dir: str | Path | None = None,
        stale_threshold_hours: int = 48,
        min_backup_count: int = 1,
    ):
        """Initialize backup health monitor.

        Args:
            config_dir: Configuration directory path (default: $CONFIG_DIR or /config)
            stale_threshold_hours: Hours before considering backups stale
            min_backup_count: Minimum number of backups that should exist
        """
        if config_dir is None:
            config_dir = Path(os.environ.get("CONFIG_DIR", "/config"))
        self.config_dir = Path(config_dir)
        self.backups_dir = self.config_dir / "backups"
        self.stale_threshold_hours = stale_threshold_hours
        self.min_backup_count = min_backup_count
        self.event_bus = get_event_bus()

        # Metrics tracking
        self._metrics: dict[str, Any] = {
            "last_backup_timestamp": None,
            "backup_count": 0,
            "total_size_bytes": 0,
            "last_backup_size_bytes": 0,
            "failed_backup_count": 0,
            "successful_backup_count": 0,
            "last_restore_timestamp": None,
            "failed_restore_count": 0,
            "successful_restore_count": 0,
            "pre_restore_snapshots_count": 0,
            "rollback_count": 0,
        }

    def check_backup_health(self) -> dict[str, Any]:
        """Check backup health and return status.

        Returns:
            dict: Health status including backup count, age, size, and alerts
        """
        try:
            backups = list_backups(self.backups_dir)
            backup_count = len(backups)

            health = {
                "status": "ok",
                "backup_count": backup_count,
                "backups_dir": str(self.backups_dir),
                "alerts": [],
            }

            if backup_count == 0:
                health["status"] = "error"
                health["alerts"].append(
                    {
                        "level": "error",
                        "message": "No backups found",
                        "recommendation": "Create a backup immediately",
                    }
                )
                self._publish_alert(
                    BackupEvents.BACKUP_STALE,
                    "No backups exist",
                    {"backup_count": 0},
                    level="error",
                )
                return health

            # Check minimum backup count
            if backup_count < self.min_backup_count:
                health["status"] = "warning"
                health["alerts"].append(
                    {
                        "level": "warning",
                        "message": f"Only {backup_count} backup(s) found",
                        "recommendation": f"Maintain at least {self.min_backup_count} backups",
                    }
                )

            # Check most recent backup
            latest = backups[0]
            health["last_backup_name"] = latest.get("name", "unknown")
            health["last_backup_size_bytes"] = latest.get("size", 0)
            health["last_backup_size_human"] = self._format_size(latest.get("size", 0))

            timestamp_str = latest.get("timestamp")
            if timestamp_str:
                health["last_backup_timestamp"] = timestamp_str
                try:
                    last_backup_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    age_hours = (datetime.now(UTC) - last_backup_time).total_seconds() / 3600
                    health["last_backup_age_hours"] = round(age_hours, 1)

                    if age_hours > self.stale_threshold_hours:
                        health["status"] = (
                            "warning" if health["status"] == "ok" else health["status"]
                        )
                        health["alerts"].append(
                            {
                                "level": "warning",
                                "message": f"Latest backup is {round(age_hours)} hours old",
                                "recommendation": f"Backups should be created at least every {self.stale_threshold_hours} hours",
                            }
                        )
                        self._publish_alert(
                            BackupEvents.BACKUP_STALE,
                            f"Latest backup is {round(age_hours)} hours old",
                            {"age_hours": age_hours, "threshold_hours": self.stale_threshold_hours},
                            level="warning",
                        )
                except Exception as e:  # nosec B110
                    logger.warning(f"Failed to parse backup timestamp: {e}")

            # Calculate total size
            total_size = sum(b.get("size", 0) for b in backups)
            health["total_size_bytes"] = total_size
            health["total_size_human"] = self._format_size(total_size)

            # Check oldest backup
            if backups:
                oldest = backups[-1]
                oldest_timestamp = oldest.get("timestamp")
                if oldest_timestamp:
                    try:
                        oldest_time = datetime.fromisoformat(
                            oldest_timestamp.replace("Z", "+00:00")
                        )
                        age_days = (datetime.now(UTC) - oldest_time).days
                        health["oldest_backup_age_days"] = age_days
                    except Exception:  # nosec B110
                        pass

            return health

        except Exception as e:  # nosec B110
            logger.error(f"Backup health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "alerts": [
                    {
                        "level": "error",
                        "message": f"Health check failed: {e}",
                        "recommendation": "Check backup system configuration",
                    }
                ],
            }

    def record_backup_created(self, backup_path: str | Path, success: bool = True) -> None:
        """Record a backup creation event.

        Args:
            backup_path: Path to the created backup
            success: Whether the backup was successful
        """
        if success:
            self._metrics["successful_backup_count"] += 1
            self._metrics["last_backup_timestamp"] = datetime.now(UTC).isoformat()

            try:
                info = get_backup_info(backup_path)
                if info:
                    size = info.get("size", 0)
                    self._metrics["last_backup_size_bytes"] = size
            except Exception:  # nosec B110
                pass

            self._publish_alert(
                BackupEvents.BACKUP_CREATED,
                f"Backup created: {Path(backup_path).name}",
                {"backup_path": str(backup_path)},
                level="info",
            )
        else:
            self._metrics["failed_backup_count"] += 1
            self._publish_alert(
                BackupEvents.BACKUP_FAILED,
                f"Backup creation failed: {Path(backup_path).name}",
                {"backup_path": str(backup_path)},
                level="error",
            )

    def record_backup_restored(
        self, backup_path: str | Path, success: bool = True, rollback: bool = False
    ) -> None:
        """Record a backup restore event.

        Args:
            backup_path: Path to the restored backup
            success: Whether the restore was successful
            rollback: Whether this was a rollback operation
        """
        if rollback:
            self._metrics["rollback_count"] += 1
            self._publish_alert(
                BackupEvents.RESTORE_ROLLBACK_EXECUTED,
                f"Rollback executed from: {Path(backup_path).name}",
                {"backup_path": str(backup_path)},
                level="warning",
            )
            return

        if success:
            self._metrics["successful_restore_count"] += 1
            self._metrics["last_restore_timestamp"] = datetime.now(UTC).isoformat()

            self._publish_alert(
                BackupEvents.BACKUP_RESTORED,
                f"Backup restored: {Path(backup_path).name}",
                {"backup_path": str(backup_path)},
                level="info",
            )
        else:
            self._metrics["failed_restore_count"] += 1
            self._publish_alert(
                BackupEvents.BACKUP_RESTORE_FAILED,
                f"Backup restore failed: {Path(backup_path).name}",
                {"backup_path": str(backup_path)},
                level="error",
            )

    def record_pre_restore_snapshot(self, snapshot_path: str | Path) -> None:
        """Record creation of a pre-restore snapshot.

        Args:
            snapshot_path: Path to the snapshot file
        """
        self._metrics["pre_restore_snapshots_count"] += 1
        self._publish_alert(
            BackupEvents.PRE_RESTORE_SNAPSHOT_CREATED,
            f"Pre-restore snapshot created: {Path(snapshot_path).name}",
            {"snapshot_path": str(snapshot_path)},
            level="info",
        )

    def record_backup_pruned(self, removed_count: int) -> None:
        """Record a backup pruning event.

        Args:
            removed_count: Number of backups removed
        """
        self._publish_alert(
            BackupEvents.BACKUP_PRUNED,
            f"Pruned {removed_count} backup(s)",
            {"removed_count": removed_count},
            level="info",
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get current backup metrics.

        Returns:
            dict: Current metrics including counts, timestamps, and sizes
        """
        # Update backup count and size from current backups
        try:
            backups = list_backups(self.backups_dir)
            self._metrics["backup_count"] = len(backups)
            self._metrics["total_size_bytes"] = sum(b.get("size", 0) for b in backups)

            if backups:
                latest = backups[0]
                self._metrics["last_backup_timestamp"] = latest.get("timestamp")
        except Exception:  # nosec B110
            pass

        return self._metrics.copy()

    def _publish_alert(
        self, event_type: str, message: str, data: dict[str, Any], level: str = "info"
    ) -> None:
        """Publish an alert event to the event bus.

        Args:
            event_type: Type of event
            message: Human-readable message
            data: Additional event data
            level: Alert level (info, warning, error)
        """
        try:
            self.event_bus.publish_simple(
                event_type,
                data={
                    "message": message,
                    "level": level,
                    "timestamp": datetime.now(UTC).isoformat(),
                    **data,
                },
                source="backup_monitor",
            )
            logger.log(
                self._get_log_level(level),
                f"Backup alert: {message}",
                extra={"event_type": event_type, **data},
            )
        except Exception as e:  # nosec B110
            logger.error(f"Failed to publish backup alert: {e}")

    @staticmethod
    def _get_log_level(level: str) -> int:
        """Convert alert level to logging level."""
        return {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }.get(level, logging.INFO)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human-readable string."""
        size_float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"


# Global instance for easy access
_global_monitor: BackupHealthMonitor | None = None


def get_backup_monitor() -> BackupHealthMonitor:
    """Get the global backup health monitor instance."""
    global _global_monitor  # noqa: PLW0603
    if _global_monitor is None:
        _global_monitor = BackupHealthMonitor()
    return _global_monitor
