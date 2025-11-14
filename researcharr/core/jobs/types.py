"""Type definitions for job queue system."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    """Job lifecycle states."""

    PENDING = "pending"  # Queued, not started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed after all retries
    CANCELLED = "cancelled"  # Manually cancelled
    RETRYING = "retrying"  # Failed, will retry
    DEAD_LETTER = "dead_letter"  # Permanently failed


class JobPriority(int, Enum):
    """Job priority levels (higher = more urgent)."""

    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 30


@dataclass
class JobDefinition:
    """Definition of work to be performed.

    Attributes:
        id: Unique job identifier
        name: Human-readable job name
        handler: Fully qualified function path (e.g., 'researcharr.tasks.process_media')
        args: Positional arguments for handler
        kwargs: Keyword arguments for handler
        priority: Job priority level
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        retry_backoff: Multiplier for exponential backoff
        timeout: Maximum execution time in seconds
        tags: Arbitrary metadata tags
        created_at: Job creation timestamp
        depends_on: List of job IDs this job depends on
    """

    # Identity
    id: UUID = field(default_factory=uuid4)
    name: str = ""

    # Execution
    handler: str = ""
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)

    # Scheduling
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds
    retry_backoff: float = 2.0  # Multiplier for exponential backoff
    timeout: float | None = None  # Max execution time in seconds

    # Metadata
    tags: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Dependencies (Phase 3)
    depends_on: list[UUID] = field(default_factory=list)
    # Scheduling (UTC timestamp when job becomes eligible). None => immediate.
    scheduled_at: datetime | None = None

    def __post_init__(self):
        """Validate job definition."""
        if not self.handler:
            raise ValueError("Job handler must be specified")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.retry_backoff <= 0:
            raise ValueError("retry_backoff must be positive")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")

        # Auto-generate name from handler if not provided
        if not self.name:
            self.name = self.handler.split(".")[-1]

        # Convert string UUID to UUID object if needed
        if isinstance(self.id, str):
            self.id = UUID(self.id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert non-serializable types
        data["id"] = str(self.id)
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        data["depends_on"] = [str(dep_id) for dep_id in self.depends_on]
        if self.scheduled_at:
            data["scheduled_at"] = self.scheduled_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobDefinition:
        """Create from dictionary."""
        # Convert serialized types back
        data = data.copy()
        data["id"] = UUID(data["id"])
        data["priority"] = JobPriority(data["priority"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["depends_on"] = [UUID(dep_id) for dep_id in data.get("depends_on", [])]
        # Convert args list to tuple
        if "args" in data and isinstance(data["args"], list):
            data["args"] = tuple(data["args"])
        if data.get("scheduled_at"):
            try:
                data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"])
            except Exception:
                data["scheduled_at"] = None
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> JobDefinition:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class JobResult:
    """Result of job execution.

    Attributes:
        job_id: Job identifier
        status: Final job status
        result: Execution result (if successful)
        error: Error message/traceback (if failed)
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        attempts: Number of execution attempts
        worker_id: ID of worker that executed the job
    """

    job_id: UUID
    status: JobStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    worker_id: str | None = None

    @property
    def duration(self) -> float | None:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["job_id"] = str(self.job_id)
        data["status"] = self.status.value
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        # Handle non-serializable results
        if self.result is not None:
            try:
                json.dumps(self.result)
            except (TypeError, ValueError):
                data["result"] = str(self.result)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobResult:
        """Create from dictionary."""
        data = data.copy()
        data["job_id"] = UUID(data["job_id"])
        data["status"] = JobStatus(data["status"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> JobResult:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class JobProgress:
    """Progress information for long-running jobs.

    Attributes:
        job_id: Job identifier
        current: Current progress value
        total: Total expected value (optional)
        message: Human-readable progress message
        metadata: Arbitrary progress metadata
        updated_at: Last update timestamp
    """

    job_id: UUID
    current: int = 0
    total: int | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def percentage(self) -> float | None:
        """Progress as percentage (0-100)."""
        if self.total and self.total > 0:
            return (self.current / self.total) * 100
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["job_id"] = str(self.job_id)
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobProgress:
        """Create from dictionary."""
        data = data.copy()
        data["job_id"] = UUID(data["job_id"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> JobProgress:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
