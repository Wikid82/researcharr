"""Abstract interfaces for job queue implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from .types import JobDefinition, JobResult, JobStatus


class JobQueue(ABC):
    """Abstract interface for job queue implementations.

    This interface allows swapping between different queue backends:
    - In-memory (development/testing)
    - Redis (production, single/multi-node)
    - Celery (distributed, advanced features)
    - RQ (simple distributed)
    """

    @abstractmethod
    async def submit(self, job: JobDefinition) -> UUID:
        """Submit a job to the queue.

        Args:
            job: Job definition with handler, args, priority, etc.

        Returns:
            job_id: UUID of the submitted job

        Raises:
            ValueError: If job validation fails
            QueueFullError: If queue is at capacity
        """

    @abstractmethod
    async def get_next(self, worker_id: str) -> JobDefinition | None:
        """Get the next job from queue for a worker.

        Jobs are ordered by:
        1. Priority (CRITICAL > HIGH > NORMAL > LOW)
        2. Creation time (FIFO within same priority)

        Args:
            worker_id: Unique identifier of the requesting worker

        Returns:
            JobDefinition if available, None if queue empty

        Note:
            This method should atomically mark the job as assigned
            to prevent multiple workers from getting the same job.
        """

    @abstractmethod
    async def complete(self, job_id: UUID, result: JobResult) -> None:
        """Mark job as completed with result.

        Args:
            job_id: Job identifier
            result: Execution result with status, output, duration, etc.

        Raises:
            JobNotFoundError: If job doesn't exist
        """

    @abstractmethod
    async def fail(self, job_id: UUID, error: str, retry: bool = True) -> None:
        """Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message/traceback
            retry: Whether to retry (if retries remaining)

        Raises:
            JobNotFoundError: If job doesn't exist

        Note:
            If retry=True and retries remain, job should be requeued
            with exponential backoff delay. Otherwise, move to dead letter.
        """

    @abstractmethod
    async def cancel(self, job_id: UUID) -> bool:
        """Cancel a pending job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if already running/completed

        Note:
            Cannot cancel jobs that are already running.
        """

    @abstractmethod
    async def get_status(self, job_id: UUID) -> JobStatus | None:
        """Get current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Current JobStatus, or None if job not found
        """

    @abstractmethod
    async def get_result(self, job_id: UUID) -> JobResult | None:
        """Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            JobResult if job completed, None if not found or not finished
        """

    @abstractmethod
    async def list_jobs(
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
            List of job definitions matching criteria
        """

    @abstractmethod
    async def get_dead_letters(self, limit: int = 100) -> list[JobDefinition]:
        """Get jobs that failed permanently (dead letter queue).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of permanently failed jobs
        """

    @abstractmethod
    async def requeue_dead_letter(self, job_id: UUID) -> bool:
        """Move a dead-letter job back to pending queue.

        Args:
            job_id: Job identifier

        Returns:
            True if requeued, False if job not in dead letter queue

        Note:
            Resets retry counter when requeuing.
        """

    @abstractmethod
    async def purge(self, status: JobStatus | None = None) -> int:
        """Remove jobs from queue.

        Args:
            status: Remove only jobs with this status (None = all jobs)

        Returns:
            Number of jobs removed

        Warning:
            This operation is destructive and cannot be undone.
            Use with caution in production.
        """

    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """Get queue metrics (size, throughput, etc.).

        Returns:
            Dictionary with metrics:
            {
                'pending': int,  # Jobs waiting to execute
                'running': int,  # Jobs currently executing
                'completed': int,  # Successfully completed
                'failed': int,  # Failed after retries
                'dead_letter': int,  # Permanently failed
                'total_processed': int,  # Lifetime job count
                'avg_wait_time': float,  # Average queue time in seconds
                'avg_exec_time': float,  # Average execution time
            }
        """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the queue backend.

        Called once at application startup. Use this to:
        - Establish connections (Redis, database)
        - Load pending jobs from storage
        - Validate configuration
        - Set up monitoring

        Raises:
            ConnectionError: If unable to connect to backend
            ConfigurationError: If configuration is invalid
        """

    @abstractmethod
    async def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the queue backend.

        Args:
            graceful: If True, wait for running jobs to complete

        Note:
            Should clean up connections and resources.
            If graceful=False, may interrupt running jobs.
        """
