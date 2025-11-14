"""Example: Integrating Job Queue with Researcharr.

This example shows how to integrate the job queue system with
existing researcharr services like backup processing.
"""

import asyncio
import logging

from researcharr.core import JobService, JobPriority

logger = logging.getLogger(__name__)


# Example 1: Wrap existing backup function
async def process_backup_job(job, progress):
    """Job handler for backup processing.

    Args:
        job: JobDefinition with args=(backup_config,)
        progress: Progress callback
    """
    from researcharr.backups import BackupManager

    backup_config = job.args[0]

    await progress(0, 100, "Initializing backup")

    # Create backup manager
    manager = BackupManager(config=backup_config)

    await progress(20, 100, "Starting backup")

    # Run backup (wrap sync code if needed)
    result = await asyncio.to_thread(manager.create_backup)

    await progress(80, 100, "Finalizing")

    # Cleanup
    await asyncio.to_thread(manager.cleanup_old_backups)

    await progress(100, 100, "Complete")

    return {
        "backup_id": result.id,
        "size": result.size,
        "location": result.path,
    }


# Example 2: Media processing with progress
async def process_media_job(job, progress):
    """Process media item with detailed progress.

    Args:
        job: JobDefinition with args=(media_id,), kwargs={quality, options}
    """
    media_id = job.args[0]
    quality = job.kwargs.get("quality", "medium")

    # Simulate multi-step processing
    steps = ["download", "analyze", "process", "upload"]

    for i, step in enumerate(steps):
        await progress(i * 25, 100, f"Step: {step}")

        # Do actual work
        await asyncio.sleep(1)  # Replace with real processing

    await progress(100, 100, "Complete")

    return {
        "media_id": media_id,
        "quality": quality,
        "processed": True,
    }


# Example 3: Database cleanup job
async def cleanup_database_job(job, progress):
    """Clean up old database records.

    Args:
        job: JobDefinition with kwargs={days_old, dry_run}
    """
    from researcharr.core import DatabaseService

    days_old = job.kwargs.get("days_old", 30)
    dry_run = job.kwargs.get("dry_run", False)

    db = DatabaseService()

    await progress(0, 100, "Counting old records")

    # Count records to delete
    count = await asyncio.to_thread(
        lambda: db.count_old_records(days_old=days_old)
    )

    await progress(25, 100, f"Found {count} old records")

    if not dry_run:
        # Delete in batches
        batch_size = 1000
        deleted = 0

        while deleted < count:
            batch = min(batch_size, count - deleted)
            await asyncio.to_thread(
                lambda: db.delete_old_records(limit=batch)
            )
            deleted += batch

            progress_pct = 25 + (deleted / count * 75)
            await progress(int(progress_pct), 100, f"Deleted {deleted}/{count}")

    await progress(100, 100, f"Cleanup complete ({'dry run' if dry_run else 'deleted'})")

    return {
        "found": count,
        "deleted": count if not dry_run else 0,
        "dry_run": dry_run,
    }


async def setup_job_service():
    """Initialize job service and register handlers.

    Returns:
        JobService: Configured job service
    """
    # Create service
    service = JobService(
        redis_url="redis://localhost:6379/0",
    )

    await service.initialize()

    # Register handlers
    service.register_handler("process_backup", process_backup_job)
    service.register_handler("process_media", process_media_job)
    service.register_handler("cleanup_database", cleanup_database_job)

    # Start workers (uses CPU count by default)
    await service.start_workers()

    logger.info("Job service initialized with handlers: backup, media, cleanup")

    return service


async def integrate_with_scheduler(job_service, scheduler):
    """Integrate job queue with APScheduler.

    Args:
        job_service: JobService instance
        scheduler: APScheduler instance
    """
    from apscheduler.triggers.cron import CronTrigger

    # Schedule daily backup at 2 AM
    async def submit_daily_backup():
        from researcharr.config import get_config

        config = get_config()
        backup_config = config.get("backup", {})

        job_id = await job_service.submit_job(
            "process_backup",
            args=(backup_config,),
            priority=JobPriority.HIGH,
        )

        logger.info(f"Scheduled backup job: {job_id}")

    scheduler.add_job(
        submit_daily_backup,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_backup",
        name="Daily Backup",
    )

    # Schedule weekly database cleanup
    async def submit_weekly_cleanup():
        job_id = await job_service.submit_job(
            "cleanup_database",
            kwargs={"days_old": 90, "dry_run": False},
            priority=JobPriority.LOW,
        )

        logger.info(f"Scheduled cleanup job: {job_id}")

    scheduler.add_job(
        submit_weekly_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_cleanup",
        name="Weekly Cleanup",
    )

    logger.info("Job queue integrated with scheduler")


async def integrate_with_event_bus(job_service, event_bus):
    """Listen for events and submit jobs.

    Args:
        job_service: JobService instance
        event_bus: EventBus instance
    """

    async def on_media_added(event):
        """Handle media.added event by submitting processing job."""
        media_id = event.data.get("media_id")
        quality = event.data.get("quality", "medium")

        job_id = await job_service.submit_job(
            "process_media",
            args=(media_id,),
            kwargs={"quality": quality},
            priority=JobPriority.NORMAL,
        )

        logger.info(f"Submitted media processing job {job_id} for media {media_id}")

    # Subscribe to events
    event_bus.subscribe("media.added", on_media_added)

    logger.info("Job queue integrated with event bus")


async def example_usage():
    """Example of using the job service."""
    # Setup
    service = await setup_job_service()

    try:
        # Submit a backup job
        backup_job_id = await service.submit_job(
            "process_backup",
            args=({"path": "/backups", "retention": 7},),
            priority=JobPriority.HIGH,
        )

        print(f"Backup job submitted: {backup_job_id}")

        # Submit media processing jobs
        media_ids = [123, 456, 789]
        media_jobs = []

        for media_id in media_ids:
            job_id = await service.submit_job(
                "process_media",
                args=(media_id,),
                kwargs={"quality": "high"},
                priority=JobPriority.NORMAL,
            )
            media_jobs.append(job_id)

        print(f"Media jobs submitted: {len(media_jobs)}")

        # Wait for backup to complete
        while True:
            status = await service.get_job_status(backup_job_id)
            if status in ["completed", "failed", "dead_letter"]:
                break
            await asyncio.sleep(1)

        # Get result
        result = await service.get_job_result(backup_job_id)
        if result:
            print(f"Backup completed in {result.duration:.2f}s")
            print(f"Result: {result.result}")

        # Check metrics
        metrics = await service.get_metrics()
        print(f"\nQueue metrics:")
        print(f"  Pending: {metrics['queue']['pending']}")
        print(f"  Running: {metrics['queue']['running']}")
        print(f"  Completed: {metrics['queue']['completed']}")
        print(f"\nWorker metrics:")
        print(f"  Total: {metrics['workers']['total']}")
        print(f"  Idle: {metrics['workers']['idle']}")
        print(f"  Busy: {metrics['workers']['busy']}")

    finally:
        # Cleanup
        await service.shutdown(graceful=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
