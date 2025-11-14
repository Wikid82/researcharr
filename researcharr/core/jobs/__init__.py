"""Job Queue and Task Management system.

This module provides a flexible, production-ready job queue system with:

Example:
    Basic usage:

    >>> job_service = JobService(queue, workers, event_bus, metrics)
    >>> job_service.register_handler('process_media', process_media_handler)
    >>> job_id = await job_service.submit_job('process_media', args=(123,))
    >>> result = await job_service.get_job_result(job_id)
"""

from .api import jobs_bp
from .handlers_backups import (
    register_backup_handlers as register_backup_job_handlers,
)
from .queue import JobQueue
from .service import JobService
from .types import (
    JobDefinition,
    JobPriority,
    JobProgress,
    JobResult,
    JobStatus,
)
from .worker import WorkerInfo, WorkerPool, WorkerStatus

__all__ = [
    # Types
    "JobDefinition",
    "JobPriority",
    "JobProgress",
    "JobResult",
    "JobStatus",
    # Queue
    "JobQueue",
    # Workers
    "WorkerInfo",
    "WorkerPool",
    "WorkerStatus",
    # Service
    "JobService",
    # API
    "jobs_bp",
    "register_backup_job_handlers",
]
