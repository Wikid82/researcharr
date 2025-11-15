"""Example: Integrating the synchronous Job Queue with Researcharr services."""

from __future__ import annotations

import logging
import time
from typing import Any

from researcharr.core import JobPriority, JobService

logger = logging.getLogger(__name__)


def process_backup_job(job, progress):
    """Job handler for backup processing tasks."""
    from researcharr.backups import BackupManager

    backup_config = job.args[0]

    progress(0, 100, "Initializing backup")

    manager = BackupManager(config=backup_config)
    progress(20, 100, "Starting backup")

    result = manager.create_backup()

    progress(80, 100, "Cleaning up old backups")
    manager.cleanup_old_backups()

    progress(100, 100, "Complete")
    return {
        "backup_id": result.id,
        "size": result.size,
        "location": result.path,
    }


def process_media_job(job, progress):
    """Process media items with detailed progress updates."""
    media_id = job.args[0]
    quality = job.kwargs.get("quality", "medium")

    steps = ["download", "analyze", "process", "upload"]
    for i, step in enumerate(steps):
        progress(i * 25, 100, f"Step: {step}")
        time.sleep(1)

    progress(100, 100, "Complete")
    return {
        "media_id": media_id,
        "quality": quality,
        "processed": True,
    }


def cleanup_database_job(job, progress):
    """Clean up old database records."""
    from researcharr.core import DatabaseService

    days_old = job.kwargs.get("days_old", 30)
    dry_run = job.kwargs.get("dry_run", False)

    db = DatabaseService()

    progress(0, 100, "Counting old records")
    count = db.count_old_records(days_old=days_old)
    progress(25, 100, f"Found {count} old records")

    if not dry_run:
        batch_size = 1000
        deleted = 0
        while deleted < count:
            batch = min(batch_size, count - deleted)
            db.delete_old_records(limit=batch)
            deleted += batch
            progress_pct = 25 + (deleted / max(count, 1) * 75)
            progress(int(progress_pct), 100, f"Deleted {deleted}/{count}")

    progress(100, 100, f"Cleanup complete ({'dry run' if dry_run else 'deleted'})")
    return {
        "found": count,
        "deleted": count if not dry_run else 0,
        "dry_run": dry_run,
    }


def setup_job_service(redis_url: str = "redis://localhost:6379/0") -> JobService:
    """Initialize job service and register handlers."""
    service = JobService(redis_url=redis_url)
    service.initialize()

    service.register_handler("process_backup", process_backup_job)
    service.register_handler("process_media", process_media_job)
    service.register_handler("cleanup_database", cleanup_database_job)

    service.start_workers()
    logger.info("Job service initialized with handlers: backup, media, cleanup")
    return service


def integrate_with_scheduler(job_service: JobService, scheduler: Any) -> None:
    """Integrate job queue with APScheduler."""
    from apscheduler.triggers.cron import CronTrigger

    from researcharr.config import get_config

    def submit_daily_backup() -> None:
        backup_config = get_config().get("backup", {})
        job_id = job_service.submit_job(
            "process_backup",
            args=(backup_config,),
            priority=JobPriority.HIGH,
        )
        logger.info("Scheduled backup job %s", job_id)

    scheduler.add_job(
        submit_daily_backup,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_backup",
        name="Daily Backup",
    )

    def submit_weekly_cleanup() -> None:
        job_id = job_service.submit_job(
            "cleanup_database",
            kwargs={"days_old": 90, "dry_run": False},
            priority=JobPriority.LOW,
        )
        logger.info("Scheduled cleanup job %s", job_id)

    scheduler.add_job(
        submit_weekly_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_cleanup",
        name="Weekly Cleanup",
    )

    logger.info("Job queue integrated with scheduler")


def integrate_with_event_bus(job_service: JobService, event_bus: Any) -> None:
    """Submit jobs in response to events."""

    def on_media_added(event):
        media_id = event.data.get("media_id")
        quality = event.data.get("quality", "medium")
        job_id = job_service.submit_job(
            "process_media",
            args=(media_id,),
            kwargs={"quality": quality},
            priority=JobPriority.NORMAL,
        )
        logger.info("Submitted media processing job %s for media %s", job_id, media_id)

    event_bus.subscribe("media.added", on_media_added)


def example_usage() -> None:
    """Demonstrate synchronous job service usage."""
    service = setup_job_service()

    try:
        backup_job_id = service.submit_job(
            "process_backup",
            args=({"path": "/backups", "retention": 7},),
            priority=JobPriority.HIGH,
        )
        logger.info("Backup job submitted: %s", backup_job_id)

        media_jobs = []
        for media_id in (123, 456, 789):
            job_id = service.submit_job(
                "process_media",
                args=(media_id,),
                kwargs={"quality": "high"},
                priority=JobPriority.NORMAL,
            )
            media_jobs.append(job_id)
        logger.info("Submitted %d media jobs", len(media_jobs))

        while True:
            status = service.get_job_status(backup_job_id)
            if status and status.value in {"completed", "failed", "dead_letter"}:
                break
            time.sleep(1)

        result = service.get_job_result(backup_job_id)
        if result:
            logger.info("Backup completed in %ss", result.duration)
            logger.info("Result: %s", result.result)

        metrics = service.get_metrics()
        logger.info("Queue metrics: %s", metrics["queue"])
        logger.info("Worker metrics: %s", metrics["workers"])

    finally:
        service.shutdown(graceful=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
