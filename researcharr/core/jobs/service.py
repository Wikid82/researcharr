"""High-level service for job management and orchestration."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from .threaded_worker import ThreadedWorkerPool
from .queue import JobQueue
from .redis_queue import RedisJobQueue
from .types import JobDefinition, JobPriority, JobResult, JobStatus
from .worker import WorkerPool

if TYPE_CHECKING:
    from researcharr.core.events import EventBus

logger = logging.getLogger(__name__)


class JobService:
    """High-level service for job management.

    Coordinates between queue, workers, events, and metrics.
    Provides simple API for submitting and tracking jobs.
    """

    def __init__(
        self,
        queue: JobQueue | None = None,
        worker_pool: WorkerPool | None = None,
        event_bus: EventBus | None = None,
        redis_url: str | None = None,
    ):
        """Initialize job service.

        Args:
            queue: Job queue implementation (default: RedisJobQueue)
            worker_pool: Worker pool implementation (default: ThreadedWorkerPool)
            event_bus: Event bus for publishing events
            redis_url: Redis URL (required if queue not provided)
        """
        # Event bus
        self._events = event_bus

        # Create queue if not provided
        if queue is None:
            if redis_url is None:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            queue = RedisJobQueue(redis_url=redis_url)

        self._queue = queue

        # Create worker pool if not provided
        if worker_pool is None:
            worker_pool = ThreadedWorkerPool(
                queue=self._queue,
                event_callback=self._publish_event if self._events else None,
            )

        self._workers = worker_pool
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the job service."""
        if self._initialized:
            return

        # Initialize queue
        self._queue.initialize()

        self._initialized = True
        logger.info("Job service initialized")

    def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the job service.

        Args:
            graceful: Wait for running jobs to complete
        """
        if not self._initialized:
            return

        logger.info("Shutting down job service")

        # Stop workers first
        self._workers.stop(graceful=graceful)

        # Shutdown queue
        self._queue.shutdown(graceful=graceful)

        self._initialized = False
        logger.info("Job service shutdown complete")

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a job handler function.

        Args:
            name: Handler name (e.g., 'process_media')
            handler: Callable(job: JobDefinition, progress: Callable)

        Example:
            def process_media(job: JobDefinition, progress: Callable):
                progress(0, 100, "Starting...")
                # ... do work ...
                progress(100, 100, "Complete")
                return result

            service.register_handler('process_media', process_media)
        """
        if isinstance(self._workers, ThreadedWorkerPool):
            self._workers.register_handler(name, handler)
        logger.info(f"Registered job handler: {name}")

    def submit_job(
        self,
        handler: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        priority: JobPriority = JobPriority.NORMAL,
        scheduled_at: datetime | None = None,
        **options: Any,
    ) -> UUID:
        """Submit a job for execution.

        Args:
            handler: Name of registered handler
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Job priority
            **options: Additional JobDefinition fields (timeout, max_retries, etc.)

        Returns:
            job_id: UUID of submitted job

        Example:
            job_id = service.submit_job(
                'process_media',
                args=(media_id,),
                kwargs={'quality': 'high'},
                priority=JobPriority.HIGH,
                timeout=300,
            )
        """
        if not self._initialized:
            raise RuntimeError("Job service not initialized")

        job = JobDefinition(
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            scheduled_at=scheduled_at,
            **options,
        )

        job_id = self._queue.submit(job)

        # Publish event
        if self._events:
            self._publish_event(
                "job.submitted",
                {
                    "job_id": str(job_id),
                    "handler": handler,
                    "priority": priority.value,
                    "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
                },
            )

        logger.debug(f"Job {job_id} submitted (handler={handler}, priority={priority.name})")
        return job_id

    def get_job_status(self, job_id: UUID) -> JobStatus | None:
        """Get current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Current status, or None if job not found
        """
        return self._queue.get_status(job_id)

    def get_job_result(self, job_id: UUID) -> JobResult | None:
        """Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            Job result, or None if not found or not finished
        """
        return self._queue.get_result(job_id)

    def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a pending job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if already running/completed
        """
        cancelled = self._queue.cancel(job_id)
        if cancelled and self._events:
            self._publish_event("job.cancelled", {"job_id": str(job_id)})
        return cancelled

    def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobDefinition]:
        """List jobs, optionally filtered by status.

        Args:
            status: Filter by specific status (None = all jobs)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of job definitions
        """
        return self._queue.list_jobs(status=status, limit=limit, offset=offset)

    def get_dead_letters(self, limit: int = 100) -> list[JobDefinition]:
        """Get permanently failed jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of dead letter jobs
        """
        return self._queue.get_dead_letters(limit=limit)

    def retry_dead_letter(self, job_id: UUID) -> bool:
        """Retry a permanently failed job.

        Args:
            job_id: Job identifier

        Returns:
            True if requeued, False if not in dead letter queue
        """
        requeued = self._queue.requeue_dead_letter(job_id)
        if requeued and self._events:
            self._publish_event("job.requeued", {"job_id": str(job_id)})
        return requeued

    def purge_jobs(self, status: JobStatus | None = None) -> int:
        """Remove jobs from queue.

        Args:
            status: Remove only jobs with this status (None = all)

        Returns:
            Number of jobs removed

        Warning:
            This operation is destructive and cannot be undone.
        """
        count = self._queue.purge(status=status)
        if self._events:
            self._publish_event(
                "jobs.purged",
                {
                    "count": count,
                    "status": status.value if status else "all",
                },
            )
        return count

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive job system metrics.

        Returns:
            Dictionary with queue and worker metrics
        """
        queue_metrics = self._queue.get_metrics()
        worker_metrics = self._workers.get_metrics()

        return {
            "queue": queue_metrics,
            "workers": worker_metrics,
        }

    def start_workers(self, count: int | None = None) -> None:
        """Start worker processes.

        Args:
            count: Number of workers to start (default: CPU count)
        """
        if count is None:
            count = os.cpu_count() or 4

        self._workers.start(count)

        if self._events:
            self._publish_event(
                "job_service.workers_started",
                {
                    "count": count,
                },
            )

        logger.info(f"Started {count} workers")

    def stop_workers(self, graceful: bool = True) -> None:
        """Stop all workers.

        Args:
            graceful: Wait for current jobs to complete
        """
        self._workers.stop(graceful=graceful)

        if self._events:
            self._publish_event("job_service.workers_stopped", {})

        logger.info("Stopped all workers")

    def scale_workers(self, target_count: int) -> None:
        """Scale workers to target count.

        Args:
            target_count: Desired number of workers
        """
        self._workers.scale(target_count)

        if self._events:
            self._publish_event(
                "job_service.workers_scaled",
                {
                    "target_count": target_count,
                },
            )

        logger.info(f"Scaled workers to {target_count}")

    def get_workers(self) -> list[Any]:
        """Get information about all workers.

        Returns:
            List of worker information objects
        """
        return self._workers.get_workers()

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish event to event bus.

        Args:
            event_type: Event type
            data: Event data
        """
        if self._events:
            try:
                # EventBus publish_simple is synchronous but thread-safe
                self._events.publish_simple(event_type, data, source="job_service")
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")
