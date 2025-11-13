"""Backup scheduling service.

Integrates backup operations with APScheduler for automated backup execution.
"""
# basedpyright: reportArgumentType=false
# basedpyright: reportCallIssue=false

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


class BackupSchedulerService:
    """Service for scheduling automated backup operations."""

    def __init__(
        self,
        scheduler: BackgroundScheduler | None = None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize the backup scheduler service.

        Args:
            scheduler: APScheduler BackgroundScheduler instance
            config: Application configuration dictionary
        """
        self._scheduler = scheduler
        self._config = config or {}
        self._backup_job_id = "automated_backup"
        self._prune_job_id = "backup_prune"

    def setup(self) -> None:
        """Set up scheduled backup jobs based on configuration."""
        if self._scheduler is None:
            logger.warning("No scheduler provided, backup automation disabled")
            return

        backup_config = self._config.get("backups", {})

        # Check if auto backup is enabled
        if not backup_config.get("auto_backup_enabled", False):
            logger.info("Automatic backups are disabled in configuration")
            return

        # Get backup schedule (cron expression)
        backup_cron = backup_config.get("auto_backup_cron", "0 2 * * *")
        prune_cron = backup_config.get("prune_cron", "0 3 * * *")
        timezone = self._config.get("scheduling", {}).get("timezone", "UTC")

        try:
            # Import CronTrigger
            from apscheduler.triggers.cron import CronTrigger

            # Schedule backup job
            self._scheduler.add_job(
                func=self._run_backup,
                trigger=CronTrigger.from_crontab(backup_cron, timezone=timezone),
                id=self._backup_job_id,
                name="Automated Backup",
                replace_existing=True,
            )
            logger.info(f"Scheduled automated backup: {backup_cron} ({timezone})")

            # Schedule prune job
            self._scheduler.add_job(
                func=self._run_prune,
                trigger=CronTrigger.from_crontab(prune_cron, timezone=timezone),
                id=self._prune_job_id,
                name="Backup Pruning",
                replace_existing=True,
            )
            logger.info(f"Scheduled backup pruning: {prune_cron} ({timezone})")

        except Exception as e:
            logger.exception(f"Failed to schedule backup jobs: {e}")

    def _run_backup(self) -> None:
        """Execute backup operation."""
        logger.info("Running scheduled backup...")

        try:
            # Import backup functions
            import os

            from researcharr.backups import create_backup_file

            config_root = os.getenv("CONFIG_DIR", "/config")
            backup_config = self._config.get("backups", {})
            backups_dir = backup_config.get("backups_dir", os.path.join(config_root, "backups"))

            # Create backup
            backup_file = create_backup_file(
                config_root=config_root,
                backups_dir=backups_dir,
                prefix="auto",
            )

            if backup_file:
                logger.info(f"Scheduled backup created: {backup_file}")

                # Publish backup created event
                try:
                    from researcharr.monitoring.backup_monitor import (
                        BackupHealthMonitor,
                    )

                    stale_hours = backup_config.get("stale_threshold_hours", 48)
                    min_count = backup_config.get("min_backup_count", 1)
                    monitor = BackupHealthMonitor(
                        config_dir=config_root,
                        stale_threshold_hours=stale_hours,
                        min_backup_count=min_count,
                    )
                    monitor.record_backup_created(backup_file, success=True)
                except Exception as e:
                    logger.warning(f"Failed to record backup metrics: {e}")
            else:
                logger.error("Scheduled backup failed: no file created")

                # Publish backup failed event
                try:
                    from researcharr.monitoring.backup_monitor import (
                        BackupHealthMonitor,
                    )

                    stale_hours = backup_config.get("stale_threshold_hours", 48)
                    min_count = backup_config.get("min_backup_count", 1)
                    monitor = BackupHealthMonitor(
                        config_dir=config_root,
                        stale_threshold_hours=stale_hours,
                        min_backup_count=min_count,
                    )
                    monitor.record_backup_created(None, success=False, error_msg="No file created")
                except Exception as e:
                    logger.warning(f"Failed to record backup failure: {e}")

        except Exception as e:
            logger.exception(f"Scheduled backup failed: {e}")

            # Publish backup failed event
            try:
                import os

                from researcharr.core.events import get_event_bus
                from researcharr.monitoring.backup_monitor import (
                    BackupHealthMonitor,
                )

                config_root = os.getenv("CONFIG_DIR", "/config")
                from researcharr.backups import get_backup_config

                backup_config = get_backup_config(config_root)
                backups_dir = backup_config["backups_dir"]

                event_bus = get_event_bus()
                monitor = BackupHealthMonitor(backups_dir, backup_config, event_bus)
                monitor.record_backup_created(None, success=False, error=str(e))
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass

    def _run_prune(self) -> None:
        """Execute backup pruning operation."""
        logger.info("Running scheduled backup pruning...")

        try:
            # Import prune function
            import os

            from researcharr.backups import prune_backups

            config_root = os.getenv("CONFIG_DIR", "/config")
            backup_config = self._config.get("backups", {})
            backups_dir = backup_config.get("backups_dir", os.path.join(config_root, "backups"))

            # Prune backups
            prune_backups(backups_dir, backup_config)

            logger.info("Scheduled pruning completed")

            # Publish prune event
            try:
                from researcharr.core.events import get_event_bus
                from researcharr.monitoring.backup_monitor import BackupEvents

                event_bus = get_event_bus()
                event_bus.publish(
                    BackupEvents.BACKUP_PRUNED,
                    {
                        "backups_dir": backups_dir,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to publish prune event: {e}")

        except Exception as e:
            logger.exception(f"Scheduled backup pruning failed: {e}")

    def remove_jobs(self) -> None:
        """Remove scheduled backup jobs."""
        if self._scheduler is None:
            return

        try:
            if self._scheduler.get_job(self._backup_job_id):
                self._scheduler.remove_job(self._backup_job_id)
                logger.info("Removed automated backup job")
        except Exception as e:
            logger.warning(f"Failed to remove backup job: {e}")

        try:
            if self._scheduler.get_job(self._prune_job_id):
                self._scheduler.remove_job(self._prune_job_id)
                logger.info("Removed backup prune job")
        except Exception as e:
            logger.warning(f"Failed to remove prune job: {e}")

    def trigger_backup_now(self) -> bool:
        """Trigger backup immediately (outside of schedule).

        Returns:
            True if backup was triggered successfully
        """
        try:
            self._run_backup()
            return True
        except Exception as e:
            logger.exception(f"Manual backup trigger failed: {e}")
            return False

    def trigger_prune_now(self) -> bool:
        """Trigger pruning immediately (outside of schedule).

        Returns:
            True if pruning was triggered successfully
        """
        try:
            self._run_prune()
            return True
        except Exception as e:
            logger.exception(f"Manual prune trigger failed: {e}")
            return False

    def get_next_backup_time(self) -> str | None:
        """Get next scheduled backup time.

        Returns:
            ISO format timestamp string or None
        """
        if self._scheduler is None:
            return None

        try:
            job = self._scheduler.get_job(self._backup_job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get next backup time: {e}")

        return None

    def get_next_prune_time(self) -> str | None:
        """Get next scheduled prune time.

        Returns:
            ISO format timestamp string or None
        """
        if self._scheduler is None:
            return None

        try:
            job = self._scheduler.get_job(self._prune_job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get next prune time: {e}")

        return None

    def get_schedule_info(self) -> dict[str, Any]:
        """Get information about scheduled backup jobs.

        Returns:
            Dictionary with schedule information
        """
        info: dict[str, Any] = {
            "enabled": False,
            "backup_schedule": None,
            "prune_schedule": None,
            "next_backup": None,
            "next_prune": None,
        }

        if self._scheduler is None:
            return info

        backup_config = self._config.get("backups", {})
        info["enabled"] = backup_config.get("auto_backup_enabled", False)

        if info["enabled"]:
            info["backup_schedule"] = backup_config.get("auto_backup_cron")
            info["prune_schedule"] = backup_config.get("prune_cron")
            info["next_backup"] = self.get_next_backup_time()
            info["next_prune"] = self.get_next_prune_time()

        return info
