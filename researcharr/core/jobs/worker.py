"""Worker pool management interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4


class WorkerStatus(str, Enum):
    """Worker states."""

    IDLE = "idle"  # Ready to accept work
    BUSY = "busy"  # Currently executing a job
    STOPPING = "stopping"  # Shutting down gracefully
    STOPPED = "stopped"  # Fully stopped
    ERROR = "error"  # In error state, needs restart


@dataclass
class WorkerInfo:
    """Information about a worker process.

    Attributes:
        id: Unique worker identifier
        status: Current worker status
        current_job: Job currently being executed (if busy)
        started_at: Worker start timestamp
        last_heartbeat: Last health check timestamp
        jobs_completed: Number of successfully completed jobs
        jobs_failed: Number of failed jobs
        hostname: Host machine (for distributed workers)
        pid: Process ID
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    status: WorkerStatus = WorkerStatus.IDLE
    current_job: UUID | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))
    jobs_completed: int = 0
    jobs_failed: int = 0
    hostname: str = ""
    pid: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if worker is healthy (recent heartbeat).

        Returns:
            True if last heartbeat within 30 seconds, False otherwise
        """
        age = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        return age < 30  # 30 second timeout

    @property
    def uptime(self) -> float:
        """Worker uptime in seconds.

        Returns:
            Number of seconds since worker started
        """
        return (datetime.now(UTC) - self.started_at).total_seconds()


class WorkerPool(ABC):
    """Abstract interface for managing worker processes.

    Implementations can be:
    - Local: Asyncio tasks in same process
    - Multi-process: Worker processes on same host
    - Distributed: Workers across multiple hosts
    """

    @abstractmethod
    async def start(self, count: int = 1) -> None:
        """Start worker processes.

        Args:
            count: Number of workers to start

        Raises:
            ValueError: If count < 1
            RuntimeError: If workers already running
        """

    @abstractmethod
    async def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop all workers.

        Args:
            graceful: Wait for current jobs to complete
            timeout: Max time to wait for graceful shutdown (seconds)

        Note:
            If graceful=True and timeout expires, workers are forcefully stopped.
        """

    @abstractmethod
    async def scale(self, target_count: int) -> None:
        """Scale workers to target count.

        Args:
            target_count: Desired number of workers

        Note:
            If target > current, starts new workers.
            If target < current, stops excess workers gracefully.
        """

    @abstractmethod
    async def get_workers(self) -> list[WorkerInfo]:
        """Get information about all workers.

        Returns:
            List of worker information objects
        """

    @abstractmethod
    async def get_worker(self, worker_id: str) -> WorkerInfo | None:
        """Get information about a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            WorkerInfo if found, None otherwise
        """

    @abstractmethod
    async def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            True if restarted, False if worker not found

        Note:
            If worker is busy, waits for current job to complete.
        """

    @abstractmethod
    async def heartbeat(self, worker_id: str) -> None:
        """Update worker heartbeat timestamp.

        Args:
            worker_id: Worker identifier

        Note:
            Called periodically by workers to indicate health.
            Used to detect stuck/crashed workers.
        """

    @abstractmethod
    async def get_metrics(self) -> dict[str, any]:
        """Get worker pool metrics.

        Returns:
            Dictionary with metrics:
            {
                'total': int,  # Total workers
                'idle': int,  # Workers waiting for work
                'busy': int,  # Workers executing jobs
                'healthy': int,  # Workers with recent heartbeat
                'unhealthy': int,  # Workers with stale heartbeat
                'avg_jobs_per_worker': float,  # Average completed jobs
                'total_jobs_completed': int,  # Sum across all workers
                'total_jobs_failed': int,  # Sum across all workers
            }
        """
