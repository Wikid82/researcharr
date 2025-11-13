"""Database health monitoring scheduler service.

Integrates database health checks with APScheduler for automated monitoring.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


class DatabaseSchedulerService:
    """Service for scheduling automated database health checks."""

    def __init__(
        self,
        scheduler: BackgroundScheduler | None = None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize the database scheduler service.

        Args:
            scheduler: APScheduler BackgroundScheduler instance
            config: Application configuration dictionary
        """
        self._scheduler = scheduler
        self._config = config or {}
        self._health_check_job_id = "database_health_check"
        self._integrity_check_job_id = "database_integrity_check"

    def setup(self) -> None:
        """Set up scheduled database health check jobs based on configuration."""
        if self._scheduler is None:
            logger.warning("No scheduler provided, database monitoring disabled")
            return

        db_config = self._config.get("database", {}).get("monitoring", {})

        # Check if database monitoring is enabled
        if not db_config.get("enabled", True):
            logger.info("Database health monitoring is disabled in configuration")
            return

        # Get monitoring intervals
        health_check_minutes = db_config.get("health_check_interval_minutes", 5)
        integrity_check_hours = db_config.get("integrity_check_interval_hours", 24)

        try:
            # Import IntervalTrigger
            from apscheduler.triggers.interval import IntervalTrigger

            # Schedule regular health check job (every N minutes)
            self._scheduler.add_job(
                func=self._run_health_check,
                trigger=IntervalTrigger(minutes=health_check_minutes),
                id=self._health_check_job_id,
                name="Database Health Check",
                replace_existing=True,
            )
            logger.info(f"Scheduled database health checks every {health_check_minutes} minutes")

            # Schedule integrity check job (every N hours)
            self._scheduler.add_job(
                func=self._run_integrity_check,
                trigger=IntervalTrigger(hours=integrity_check_hours),
                id=self._integrity_check_job_id,
                name="Database Integrity Check",
                replace_existing=True,
            )
            logger.info(f"Scheduled database integrity checks every {integrity_check_hours} hours")

        except Exception as e:
            logger.exception(f"Failed to schedule database health check jobs: {e}")

    def _run_health_check(self) -> None:
        """Execute database health check."""
        logger.debug("Running scheduled database health check...")

        try:
            # Import database health monitor
            from researcharr.monitoring.database_monitor import (
                get_database_health_monitor,
            )

            # Get monitor instance
            monitor = get_database_health_monitor()

            # Run health check
            health = monitor.check_database_health()

            # Log results
            status = health.get("status", "unknown")
            if status == "ok":
                logger.debug("Database health check passed")
            elif status == "warning":
                logger.warning(
                    f"Database health check has warnings: {len(health.get('alerts', []))} alerts"
                )
            else:
                logger.error(
                    f"Database health check failed: {len(health.get('alerts', []))} alerts"
                )

            # Check for critical alerts
            for alert in health.get("alerts", []):
                if alert.get("level") == "error":
                    logger.error(f"Database alert: {alert.get('message')}")
                elif alert.get("level") == "warning":
                    logger.warning(f"Database alert: {alert.get('message')}")

        except Exception as e:
            logger.exception(f"Scheduled database health check failed: {e}")

    def _run_integrity_check(self) -> None:
        """Execute database integrity check."""
        logger.info("Running scheduled database integrity check...")

        try:
            # Import database health monitor
            from researcharr.monitoring.database_monitor import (
                get_database_health_monitor,
            )

            # Get monitor instance
            monitor = get_database_health_monitor()

            # Force integrity check
            result = monitor.force_integrity_check()

            if result.get("checked"):
                if result.get("status") == "ok":
                    check_time = result.get("check_time_ms", 0)
                    logger.info(f"Database integrity check passed ({check_time:.1f}ms)")
                else:
                    logger.error(f"Database integrity check failed: {result.get('result')}")
            else:
                logger.warning("Database integrity check was skipped")

        except Exception as e:
            logger.exception(f"Scheduled database integrity check failed: {e}")

    def remove_jobs(self) -> None:
        """Remove scheduled database health check jobs."""
        if self._scheduler is None:
            return

        try:
            if self._scheduler.get_job(self._health_check_job_id):
                self._scheduler.remove_job(self._health_check_job_id)
                logger.info("Removed database health check job")
        except Exception as e:
            logger.warning(f"Failed to remove health check job: {e}")

        try:
            if self._scheduler.get_job(self._integrity_check_job_id):
                self._scheduler.remove_job(self._integrity_check_job_id)
                logger.info("Removed database integrity check job")
        except Exception as e:
            logger.warning(f"Failed to remove integrity check job: {e}")

    def trigger_health_check_now(self) -> bool:
        """Trigger database health check immediately (outside of schedule).

        Returns:
            True if health check was triggered successfully
        """
        try:
            self._run_health_check()
            return True
        except Exception as e:
            logger.exception(f"Manual health check trigger failed: {e}")
            return False

    def trigger_integrity_check_now(self) -> bool:
        """Trigger database integrity check immediately (outside of schedule).

        Returns:
            True if integrity check was triggered successfully
        """
        try:
            self._run_integrity_check()
            return True
        except Exception as e:
            logger.exception(f"Manual integrity check trigger failed: {e}")
            return False

    def get_next_health_check_time(self) -> str | None:
        """Get next scheduled health check time.

        Returns:
            ISO format timestamp string or None
        """
        if self._scheduler is None:
            return None

        try:
            job = self._scheduler.get_job(self._health_check_job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get next health check time: {e}")

        return None

    def get_next_integrity_check_time(self) -> str | None:
        """Get next scheduled integrity check time.

        Returns:
            ISO format timestamp string or None
        """
        if self._scheduler is None:
            return None

        try:
            job = self._scheduler.get_job(self._integrity_check_job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get next integrity check time: {e}")

        return None

    def get_schedule_info(self) -> dict[str, Any]:
        """Get information about scheduled database health check jobs.

        Returns:
            Dictionary with schedule information
        """
        info: dict[str, Any] = {
            "enabled": False,
            "health_check_interval_minutes": None,
            "integrity_check_interval_hours": None,
            "next_health_check": None,
            "next_integrity_check": None,
        }

        if self._scheduler is None:
            return info

        db_config = self._config.get("database", {}).get("monitoring", {})
        info["enabled"] = db_config.get("enabled", True)

        if info["enabled"]:
            info["health_check_interval_minutes"] = db_config.get(
                "health_check_interval_minutes", 5
            )
            info["integrity_check_interval_hours"] = db_config.get(
                "integrity_check_interval_hours", 24
            )
            info["next_health_check"] = self.get_next_health_check_time()
            info["next_integrity_check"] = self.get_next_integrity_check_time()

        return info
