# Job Queue and Task Management - Architecture Design

**Issue**: #109  
**Status**: Design Phase  
**Date**: November 14, 2025

## Overview

Design a flexible, production-ready job queue system that supports asynchronous task execution, status tracking, retry mechanisms, and distributed worker support. The system will leverage existing infrastructure (`async_pipeline.py`, APScheduler, event bus) while maintaining clean interfaces for future migration to Celery/RQ if needed.

## Design Goals

1. **Async-First**: Built on `asyncio` for efficient resource utilization
2. **Observable**: Full job lifecycle tracking with status, progress, and metrics
3. **Resilient**: Automatic retries with exponential backoff and dead-letter queues
4. **Scalable**: Support for multiple workers and future distributed deployment
5. **Portable**: Abstract interfaces allowing backend swapping (in-memory → Redis → Celery)
6. **Integrated**: Leverage existing services (events, config, monitoring, database)

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (REST/Events)                  │
│  /api/jobs/submit  /api/jobs/{id}/status  /api/jobs/{id}   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Job Service Layer                           │
│  JobService: High-level job management & orchestration      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 Queue Implementation Layer                   │
│  JobQueue (abstract) → InMemoryQueue / RedisQueue / etc.    │
│  WorkerPool: Manages worker lifecycle & scaling             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Persistence Layer                           │
│  JobRepository: SQLAlchemy models for jobs & results        │
│  JobResultStore: Configurable result storage (DB/Redis/S3)  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Infrastructure Services                         │
│  EventBus, ConfigManager, MetricsService, Logger            │
└─────────────────────────────────────────────────────────────┘
```

## Core Interfaces

### 1. Job Definition

```python
# researcharr/core/jobs/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    """Job lifecycle states."""
    PENDING = "pending"       # Queued, not started
    RUNNING = "running"       # Currently executing
    COMPLETED = "completed"   # Successfully finished
    FAILED = "failed"         # Failed after all retries
    CANCELLED = "cancelled"   # Manually cancelled
    RETRYING = "retrying"     # Failed, will retry
    DEAD_LETTER = "dead_letter"  # Permanently failed


class JobPriority(int, Enum):
    """Job priority levels (higher = more urgent)."""
    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 30


@dataclass
class JobDefinition:
    """Definition of work to be performed."""
    
    # Identity
    id: UUID = field(default_factory=uuid4)
    name: str = ""  # e.g., "process_media_item"
    
    # Execution
    handler: str = ""  # Fully qualified function path
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    
    # Scheduling
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds
    retry_backoff: float = 2.0  # Multiplier for exponential backoff
    timeout: Optional[float] = None  # Max execution time in seconds
    
    # Metadata
    tags: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Dependencies
    depends_on: list[UUID] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate job definition."""
        if not self.handler:
            raise ValueError("Job handler must be specified")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")


@dataclass
class JobResult:
    """Result of job execution."""
    
    job_id: UUID
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    worker_id: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class JobProgress:
    """Progress information for long-running jobs."""
    
    job_id: UUID
    current: int = 0
    total: Optional[int] = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def percentage(self) -> Optional[float]:
        """Progress as percentage (0-100)."""
        if self.total and self.total > 0:
            return (self.current / self.total) * 100
        return None
```

### 2. Job Queue Interface

```python
# researcharr/core/jobs/queue.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from uuid import UUID

from .types import JobDefinition, JobResult, JobStatus


class JobQueue(ABC):
    """Abstract interface for job queue implementations."""
    
    @abstractmethod
    async def submit(self, job: JobDefinition) -> UUID:
        """Submit a job to the queue.
        
        Returns:
            job_id: UUID of the submitted job
        """
        pass
    
    @abstractmethod
    async def get_next(self, worker_id: str) -> Optional[JobDefinition]:
        """Get the next job from queue for a worker.
        
        Priority order: CRITICAL > HIGH > NORMAL > LOW
        Within same priority: FIFO
        
        Returns:
            JobDefinition if available, None if queue empty
        """
        pass
    
    @abstractmethod
    async def complete(self, job_id: UUID, result: JobResult) -> None:
        """Mark job as completed with result."""
        pass
    
    @abstractmethod
    async def fail(
        self, 
        job_id: UUID, 
        error: str, 
        retry: bool = True
    ) -> None:
        """Mark job as failed.
        
        Args:
            job_id: Job identifier
            error: Error message/traceback
            retry: Whether to retry (if retries remaining)
        """
        pass
    
    @abstractmethod
    async def cancel(self, job_id: UUID) -> bool:
        """Cancel a pending job.
        
        Returns:
            True if cancelled, False if already running/completed
        """
        pass
    
    @abstractmethod
    async def get_status(self, job_id: UUID) -> Optional[JobStatus]:
        """Get current status of a job."""
        pass
    
    @abstractmethod
    async def get_result(self, job_id: UUID) -> Optional[JobResult]:
        """Get result of a completed job."""
        pass
    
    @abstractmethod
    async def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[JobDefinition]:
        """List jobs, optionally filtered by status."""
        pass
    
    @abstractmethod
    async def get_dead_letters(self, limit: int = 100) -> list[JobDefinition]:
        """Get jobs that failed permanently (dead letter queue)."""
        pass
    
    @abstractmethod
    async def requeue_dead_letter(self, job_id: UUID) -> bool:
        """Move a dead-letter job back to pending queue."""
        pass
    
    @abstractmethod
    async def purge(self, status: Optional[JobStatus] = None) -> int:
        """Remove jobs from queue.
        
        Returns:
            Number of jobs removed
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """Get queue metrics (size, throughput, etc.)."""
        pass
```

### 3. Worker Management

```python
# researcharr/core/jobs/worker.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class WorkerStatus(str, Enum):
    """Worker states."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerInfo:
    """Information about a worker process."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    status: WorkerStatus = WorkerStatus.IDLE
    current_job: Optional[UUID] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    jobs_completed: int = 0
    jobs_failed: int = 0
    
    @property
    def is_healthy(self) -> bool:
        """Check if worker is healthy (recent heartbeat)."""
        age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return age < 30  # 30 second timeout


class WorkerPool(ABC):
    """Abstract interface for managing worker processes."""
    
    @abstractmethod
    async def start(self, count: int = 1) -> None:
        """Start worker processes.
        
        Args:
            count: Number of workers to start
        """
        pass
    
    @abstractmethod
    async def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop all workers.
        
        Args:
            graceful: Wait for current jobs to complete
            timeout: Max time to wait for graceful shutdown
        """
        pass
    
    @abstractmethod
    async def scale(self, target_count: int) -> None:
        """Scale workers to target count."""
        pass
    
    @abstractmethod
    async def get_workers(self) -> list[WorkerInfo]:
        """Get information about all workers."""
        pass
    
    @abstractmethod
    async def get_worker(self, worker_id: str) -> Optional[WorkerInfo]:
        """Get information about a specific worker."""
        pass
    
    @abstractmethod
    async def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker."""
        pass
```

### 4. Job Service

```python
# researcharr/core/jobs/service.py

from typing import Any, Callable, Optional
from uuid import UUID

from .queue import JobQueue
from .types import JobDefinition, JobPriority, JobProgress, JobResult, JobStatus
from .worker import WorkerPool


class JobService:
    """High-level service for job management."""
    
    def __init__(
        self, 
        queue: JobQueue,
        worker_pool: WorkerPool,
        event_bus: Any,  # EventBus
        metrics: Any,  # MetricsService
    ):
        self._queue = queue
        self._workers = worker_pool
        self._events = event_bus
        self._metrics = metrics
        self._handlers: dict[str, Callable] = {}
    
    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a job handler function.
        
        Args:
            name: Handler name (e.g., 'process_media')
            handler: Async callable that accepts (job_def, progress_callback)
        """
        self._handlers[name] = handler
    
    async def submit_job(
        self,
        handler: str,
        args: tuple = (),
        kwargs: dict = None,
        priority: JobPriority = JobPriority.NORMAL,
        **options
    ) -> UUID:
        """Submit a job for execution.
        
        Args:
            handler: Name of registered handler
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Job priority
            **options: Additional JobDefinition fields
            
        Returns:
            job_id: UUID of submitted job
        """
        job = JobDefinition(
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            **options
        )
        
        job_id = await self._queue.submit(job)
        
        # Publish event
        await self._events.publish('job.submitted', {
            'job_id': str(job_id),
            'handler': handler,
            'priority': priority.value
        })
        
        # Update metrics
        self._metrics.increment('jobs_submitted_total', {
            'handler': handler,
            'priority': priority.name
        })
        
        return job_id
    
    async def get_job_status(self, job_id: UUID) -> Optional[JobStatus]:
        """Get current status of a job."""
        return await self._queue.get_status(job_id)
    
    async def get_job_result(self, job_id: UUID) -> Optional[JobResult]:
        """Get result of a completed job."""
        return await self._queue.get_result(job_id)
    
    async def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a pending job."""
        cancelled = await self._queue.cancel(job_id)
        if cancelled:
            await self._events.publish('job.cancelled', {'job_id': str(job_id)})
        return cancelled
    
    async def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> list[JobDefinition]:
        """List jobs, optionally filtered by status."""
        return await self._queue.list_jobs(status=status, limit=limit)
    
    async def get_dead_letters(self) -> list[JobDefinition]:
        """Get permanently failed jobs."""
        return await self._queue.get_dead_letters()
    
    async def retry_dead_letter(self, job_id: UUID) -> bool:
        """Retry a permanently failed job."""
        return await self._queue.requeue_dead_letter(job_id)
    
    async def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive job system metrics."""
        queue_metrics = await self._queue.get_metrics()
        workers = await self._workers.get_workers()
        
        return {
            'queue': queue_metrics,
            'workers': {
                'total': len(workers),
                'idle': sum(1 for w in workers if w.status == 'idle'),
                'busy': sum(1 for w in workers if w.status == 'busy'),
                'healthy': sum(1 for w in workers if w.is_healthy),
            },
            'system': {
                'handlers_registered': len(self._handlers),
            }
        }
    
    async def start(self, worker_count: int = 1) -> None:
        """Start the job service and workers."""
        await self._workers.start(worker_count)
        await self._events.publish('job_service.started', {
            'worker_count': worker_count
        })
    
    async def stop(self, graceful: bool = True) -> None:
        """Stop the job service and workers."""
        await self._workers.stop(graceful=graceful)
        await self._events.publish('job_service.stopped', {})
```

## Implementation Phases

### Phase 1: Core Foundations (Week 1)

**Goal**: Basic job submission and execution with in-memory queue

1. **Create type definitions** (`researcharr/core/jobs/types.py`)
   - JobDefinition, JobResult, JobProgress dataclasses
   - JobStatus, JobPriority enums
   - Validation logic

2. **Implement abstract interfaces** (`researcharr/core/jobs/queue.py`, `worker.py`)
   - JobQueue abstract base class
   - WorkerPool abstract base class
   - Full interface documentation

3. **Build in-memory queue** (`researcharr/core/jobs/memory_queue.py`)
   - Priority queue using heapq
   - Simple retry logic with exponential backoff
   - Dead letter collection
   - Metrics tracking

4. **Create worker implementation** (`researcharr/core/jobs/memory_worker.py`)
   - Asyncio-based workers
   - Job execution with timeout
   - Error handling and retry
   - Heartbeat mechanism

5. **Build JobService** (`researcharr/core/jobs/service.py`)
   - Handler registration
   - Job submission with validation
   - Event publishing integration
   - Metrics integration

**Acceptance Criteria**:
- Can submit jobs and execute async handlers
- Job status transitions correctly (pending → running → completed/failed)
- Failed jobs retry with exponential backoff
- Dead letter queue captures permanently failed jobs
- Basic metrics available

### Phase 2: Persistence & Monitoring (Week 2)

**Goal**: Persist job state and add comprehensive monitoring

6. **Create database models** (`researcharr/models/job.py`)
   - Job table (id, status, handler, args, created_at, etc.)
   - JobExecution table (attempts, started_at, completed_at, error)
   - JobResult table (job_id, result_data, metadata)
   - Indexes for efficient queries

7. **Implement JobRepository** (`researcharr/repositories/job_repository.py`)
   - CRUD operations for jobs
   - Status queries with filtering
   - Result storage and retrieval
   - Execution history tracking

8. **Build persistent queue** (`researcharr/core/jobs/persistent_queue.py`)
   - Hybrid: in-memory priority queue + DB persistence
   - Load pending jobs on startup
   - Persist state changes immediately
   - Atomic operations for reliability

9. **Add progress tracking** (`researcharr/core/jobs/progress.py`)
   - Progress callback interface
   - Real-time updates via EventBus
   - Progress storage in database
   - WebSocket integration for UI

10. **Enhance monitoring** (`researcharr/core/jobs/metrics.py`)
    - Prometheus metrics exporter
    - Job throughput, latency, error rates
    - Worker utilization tracking
    - Queue depth monitoring

**Acceptance Criteria**:
- Jobs survive application restarts
- Progress updates flow to UI in real-time
- Comprehensive metrics in /metrics endpoint
- Job history queryable via repository

### Phase 3: Advanced Features (Week 3)

**Goal**: Job dependencies, scheduling, and distributed support

11. **Job dependencies** (`researcharr/core/jobs/dependencies.py`)
    - DAG validation (no cycles)
    - Dependency tracking in database
    - Automatic job triggering on parent completion
    - Parallel execution of independent jobs

12. **Scheduled jobs** (`researcharr/core/jobs/scheduler_integration.py`)
    - APScheduler integration
    - Cron-based job submission
    - One-time delayed jobs
    - Recurring job management

13. **Result storage backends** (`researcharr/core/jobs/result_store.py`)
    - Pluggable result storage (DB, Redis, S3)
    - Large result handling (avoid DB bloat)
    - Result TTL and cleanup
    - Compression for large results

14. **Distributed queue preparation** (`researcharr/core/jobs/redis_queue.py`)
    - Redis-based queue implementation
    - Multi-process worker support
    - Distributed locking
    - Horizontal scaling

**Acceptance Criteria**:
- Jobs can depend on other jobs
- Scheduled jobs execute at specified times
- Large results stored efficiently
- Multiple processes can share queue via Redis

### Phase 4: Production Hardening (Week 4)

**Goal**: Battle-test and optimize for production use

15. **Error handling enhancements**
    - Circuit breaker for failing handlers
    - Rate limiting for problematic jobs
    - Automatic quarantine of broken handlers
    - Alert integration for critical failures

16. **Performance optimization**
    - Batch job submission API
    - Connection pooling for database
    - Efficient serialization (msgpack?)
    - Query optimization with indexes

17. **Operational tooling**
    - CLI for job management (`researcharr jobs list`)
    - Admin UI endpoints
    - Job replay/requeue tools
    - Bulk operations (cancel all, purge old)

18. **Documentation and testing**
    - Comprehensive test suite (unit + integration)
    - Architecture documentation
    - API documentation
    - Migration guide for existing tasks

**Acceptance Criteria**:
- 95%+ test coverage for job system
- Performance benchmarks documented
- Production deployment guide complete
- Zero data loss under failure scenarios

## Database Schema

```sql
-- Job definitions
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    handler VARCHAR(500) NOT NULL,
    args_json TEXT,
    kwargs_json TEXT,
    priority INTEGER NOT NULL DEFAULT 10,
    status VARCHAR(50) NOT NULL,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_delay FLOAT NOT NULL DEFAULT 1.0,
    retry_backoff FLOAT NOT NULL DEFAULT 2.0,
    timeout FLOAT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    INDEX idx_status (status),
    INDEX idx_priority_created (priority DESC, created_at ASC),
    INDEX idx_handler (handler)
);

-- Job execution attempts
CREATE TABLE job_executions (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    attempt INTEGER NOT NULL,
    worker_id VARCHAR(255),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error TEXT,
    INDEX idx_job_id (job_id),
    INDEX idx_started (started_at DESC)
);

-- Job results
CREATE TABLE job_results (
    job_id UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    result_data TEXT,
    result_size INTEGER,
    storage_backend VARCHAR(50),
    storage_key VARCHAR(500),
    created_at TIMESTAMP NOT NULL
);

-- Job progress tracking
CREATE TABLE job_progress (
    job_id UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    current INTEGER NOT NULL DEFAULT 0,
    total INTEGER,
    message TEXT,
    metadata_json TEXT,
    updated_at TIMESTAMP NOT NULL
);

-- Job dependencies
CREATE TABLE job_dependencies (
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    depends_on_job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, depends_on_job_id),
    INDEX idx_depends_on (depends_on_job_id)
);
```

## Event Schema

Job lifecycle events published to EventBus:

```python
# Job submitted
'job.submitted' → {
    'job_id': str,
    'handler': str,
    'priority': int,
    'timestamp': datetime
}

# Job started
'job.started' → {
    'job_id': str,
    'worker_id': str,
    'attempt': int,
    'timestamp': datetime
}

# Job progress
'job.progress' → {
    'job_id': str,
    'current': int,
    'total': int,
    'percentage': float,
    'message': str,
    'timestamp': datetime
}

# Job completed
'job.completed' → {
    'job_id': str,
    'duration': float,
    'timestamp': datetime
}

# Job failed
'job.failed' → {
    'job_id': str,
    'error': str,
    'will_retry': bool,
    'attempts': int,
    'timestamp': datetime
}

# Job dead letter
'job.dead_letter' → {
    'job_id': str,
    'handler': str,
    'final_error': str,
    'total_attempts': int,
    'timestamp': datetime
}

# Job cancelled
'job.cancelled' → {
    'job_id': str,
    'timestamp': datetime
}
```

## Metrics

Prometheus metrics exposed:

```python
# Counters
jobs_submitted_total{handler, priority}
jobs_completed_total{handler, status}  # status: success/failed/cancelled
jobs_retried_total{handler}
jobs_dead_letter_total{handler}

# Gauges
jobs_pending{priority}
jobs_running{handler}
jobs_dead_letter
workers_total
workers_idle
workers_busy

# Histograms
job_duration_seconds{handler}
job_queue_time_seconds{priority}
job_retry_delay_seconds{handler}

# Summaries
job_result_size_bytes{handler}
```

## Configuration

```yaml
# config.yml
jobs:
  # Queue configuration
  queue:
    type: memory  # memory, redis, database
    max_size: 10000
    redis_url: redis://localhost:6379/0  # if type=redis
  
  # Worker configuration
  workers:
    count: 4
    max_jobs_per_worker: 1000  # Restart worker after N jobs
    heartbeat_interval: 10  # seconds
    shutdown_timeout: 30  # seconds
  
  # Retry configuration
  retry:
    max_attempts: 3
    base_delay: 1.0  # seconds
    backoff_multiplier: 2.0
    max_delay: 300.0  # seconds (5 minutes)
  
  # Result storage
  results:
    backend: database  # database, redis, s3
    ttl: 604800  # 7 days in seconds
    large_result_threshold: 1048576  # 1MB, store in object storage
    s3_bucket: researcharr-job-results  # if backend=s3
  
  # Dead letter queue
  dead_letter:
    max_size: 1000
    retention_days: 30
  
  # Monitoring
  monitoring:
    metrics_interval: 5  # seconds
    log_slow_jobs: true
    slow_job_threshold: 60  # seconds
```

## API Endpoints

```python
# Job submission
POST /api/jobs/submit
{
    "handler": "process_media",
    "args": [123],
    "kwargs": {"quality": "high"},
    "priority": "normal",
    "timeout": 300
}
→ {"job_id": "uuid", "status": "pending"}

# Job status
GET /api/jobs/{job_id}/status
→ {
    "job_id": "uuid",
    "status": "running",
    "progress": {"current": 50, "total": 100, "percentage": 50.0},
    "attempts": 1,
    "created_at": "2025-11-14T10:00:00Z",
    "started_at": "2025-11-14T10:00:05Z"
}

# Job result
GET /api/jobs/{job_id}/result
→ {
    "job_id": "uuid",
    "status": "completed",
    "result": {...},
    "duration": 12.5,
    "completed_at": "2025-11-14T10:00:17Z"
}

# List jobs
GET /api/jobs?status=failed&limit=50
→ {
    "jobs": [{...}, {...}],
    "total": 123,
    "page": 1
}

# Cancel job
POST /api/jobs/{job_id}/cancel
→ {"cancelled": true}

# Retry dead letter
POST /api/jobs/{job_id}/retry
→ {"job_id": "uuid", "status": "pending"}

# Job metrics
GET /api/jobs/metrics
→ {
    "queue": {"pending": 45, "size": 10000},
    "workers": {"total": 4, "idle": 2, "busy": 2},
    "throughput": {"1m": 10.5, "5m": 8.3, "15m": 9.1}
}

# Worker management
GET /api/workers
→ [
    {
        "id": "worker-1",
        "status": "busy",
        "current_job": "uuid",
        "jobs_completed": 123,
        "uptime": 3600
    }
]

POST /api/workers/scale
{"count": 8}
→ {"previous": 4, "target": 8, "status": "scaling"}
```

## Migration Path from Existing System

Current state uses:
- APScheduler for cron-based jobs
- `run_job()` function for manual execution
- Thread-based background execution
- No job tracking or retry logic

Migration approach:

1. **Wrap existing handlers**: Convert `run_job` to a job handler
   ```python
   job_service.register_handler('legacy_run_job', async_wrapper(run_job))
   ```

2. **Integrate with APScheduler**: Schedule jobs via JobService
   ```python
   scheduler.add_job(
       lambda: job_service.submit_job('legacy_run_job'),
       trigger=CronTrigger.from_crontab(cron_expr)
   )
   ```

3. **Gradual migration**: New features use JobService, old code continues
4. **Feature parity**: Once JobService has all features, deprecate old system
5. **Cleanup**: Remove old code after migration complete

## Future Enhancements

### Celery Integration

When ready for distributed processing:

```python
# researcharr/core/jobs/celery_queue.py
class CeleryJobQueue(JobQueue):
    """Celery-based distributed queue."""
    
    def __init__(self, broker_url: str, result_backend: str):
        from celery import Celery
        self.app = Celery('researcharr', broker=broker_url, backend=result_backend)
        self._configure_celery()
```

Benefits:
- Battle-tested distributed queue
- Rich ecosystem (flower, monitoring)
- Advanced features (chords, chains, groups)

Trade-offs:
- Additional dependency (Redis/RabbitMQ)
- More complex deployment
- Learning curve for operators

### RQ Integration

Lighter alternative to Celery:

```python
# researcharr/core/jobs/rq_queue.py
class RQJobQueue(JobQueue):
    """Redis Queue based implementation."""
    
    def __init__(self, redis_url: str):
        from rq import Queue
        self.queue = Queue(connection=Redis.from_url(redis_url))
```

Benefits:
- Simpler than Celery
- Just needs Redis
- Good Python integration

Trade-offs:
- Less feature-rich than Celery
- Smaller ecosystem
- Redis required

## Testing Strategy

### Unit Tests
- Each interface implementation
- Worker lifecycle
- Retry logic
- Error handling
- Metrics collection

### Integration Tests
- End-to-end job submission → execution → result
- Database persistence
- Event publishing
- Worker scaling
- Concurrent job execution

### Performance Tests
- High throughput (1000+ jobs/second)
- Large jobs (100MB+ results)
- Many workers (50+)
- Long-running jobs (hours)
- Queue depth stress test

### Failure Tests
- Database connection loss
- Worker crashes mid-job
- Handler exceptions
- Timeout handling
- Dead letter queue overflow

## Success Metrics

- **Reliability**: 99.9% job success rate (excluding expected failures)
- **Performance**: <100ms overhead per job (queue → execution)
- **Scalability**: Linear scaling to 100+ workers
- **Observability**: 100% of jobs tracked with status/progress
- **Recovery**: Zero job loss on application restart

## Next Steps

1. **Review this design** with team
2. **Create GitHub issue** for Phase 1 implementation
3. **Set up project structure** (`researcharr/core/jobs/`)
4. **Implement Phase 1** (Week 1 deliverables)
5. **Write comprehensive tests** as we build
6. **Document API** in real-time

## Questions for Team Discussion

1. **Queue backend**: Start with in-memory or go straight to Redis?
2. **Worker count**: Default to CPU count or fixed number (e.g., 4)?
3. **Result storage**: Large results in DB or always use object storage?
4. **Priority levels**: Do we need more than 4 levels (LOW/NORMAL/HIGH/CRITICAL)?
5. **Job TTL**: Auto-delete completed jobs after N days?
6. **Handler registration**: Explicit registration or auto-discovery via decorators?
7. **Distributed**: Plan for multi-instance from day 1 or add later?
8. **Monitoring**: Build custom UI or integrate with existing tools (Flower, etc.)?

---

**Document Status**: Draft for review  
**Next Review**: Before Phase 1 implementation  
**Owner**: Development Team  
**Related Issues**: #109
