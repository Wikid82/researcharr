# Job Queue System - Quick Start Guide

## Overview

The job queue system provides asynchronous task execution with:
- Redis-backed distributed queue
- Automatic retries with exponential backoff
- Priority-based execution
- Dead letter queue for failed jobs
- Real-time progress tracking
- Worker pool management

## Installation

```bash
# Install Redis
pip install redis==5.0.10

# Or update requirements
pip install -r requirements.txt
```

## Basic Usage

### 1. Initialize Job Service

```python
from researcharr.core.jobs import JobService, JobPriority

# Create service (uses REDIS_URL env var or default)
job_service = JobService(redis_url="redis://localhost:6379/0")
await job_service.initialize()

# Start workers (default: CPU count)
await job_service.start_workers(count=4)
```

### 2. Register Job Handlers

```python
from researcharr.core.jobs import JobDefinition

async def process_media(job: JobDefinition, progress_callback):
    """Process media files."""
    media_id = job.args[0]
    quality = job.kwargs.get("quality", "medium")
    
    # Report progress
    await progress_callback(0, 100, "Starting...")
    
    # Do work
    result = await do_processing(media_id, quality)
    
    # Report completion
    await progress_callback(100, 100, "Complete")
    
    return result

# Register handler
job_service.register_handler("process_media", process_media)
```

### 3. Submit Jobs

```python
# Submit a job
job_id = await job_service.submit_job(
    "process_media",
    args=(123,),
    kwargs={"quality": "high"},
    priority=JobPriority.HIGH,
    timeout=300,  # 5 minutes
    max_retries=3,
)

print(f"Job submitted: {job_id}")
```

### 4. Track Job Status

```python
# Get status
status = await job_service.get_job_status(job_id)
print(f"Status: {status}")  # PENDING, RUNNING, COMPLETED, etc.

# Wait for completion
while True:
    status = await job_service.get_job_status(job_id)
    if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.DEAD_LETTER]:
        break
    await asyncio.sleep(1)

# Get result
result = await job_service.get_job_result(job_id)
if result:
    print(f"Result: {result.result}")
    print(f"Duration: {result.duration}s")
```

## Advanced Features

### Priority Levels

```python
from researcharr.core.jobs import JobPriority

# Submit with different priorities
critical_job = await job_service.submit_job(
    "urgent_task",
    priority=JobPriority.CRITICAL,  # 30 - highest
)

high_job = await job_service.submit_job(
    "important_task",
    priority=JobPriority.HIGH,  # 20
)

normal_job = await job_service.submit_job(
    "regular_task",
    priority=JobPriority.NORMAL,  # 10 - default
)

low_job = await job_service.submit_job(
    "background_task",
    priority=JobPriority.LOW,  # 0 - lowest
)
```

### Retry Configuration

```python
job_id = await job_service.submit_job(
    "flaky_task",
    max_retries=5,  # Try up to 5 times
    retry_delay=2.0,  # Start with 2 second delay
    retry_backoff=2.0,  # Double delay each retry
    # Delays: 2s, 4s, 8s, 16s, 32s (capped at 300s)
)
```

### Progress Tracking

```python
async def long_running_task(job: JobDefinition, progress_callback):
    """Task with progress updates."""
    items = job.args[0]
    
    for i, item in enumerate(items):
        # Process item
        await process_item(item)
        
        # Update progress
        await progress_callback(
            current=i + 1,
            total=len(items),
            message=f"Processed {i + 1}/{len(items)} items",
        )
    
    return {"processed": len(items)}

# Listen for progress events (if event bus configured)
# Events: job.started, job.progress, job.completed, job.failed
```

### Dead Letter Queue

```python
# Get failed jobs
dead_letters = await job_service.get_dead_letters(limit=100)

for job in dead_letters:
    print(f"Failed job: {job.id} - {job.handler}")

# Retry a failed job
job_id = dead_letters[0].id
requeued = await job_service.retry_dead_letter(job_id)
if requeued:
    print(f"Job {job_id} requeued")
```

### Worker Management

```python
# Get worker info
workers = await job_service.get_workers()
for worker in workers:
    print(f"Worker {worker.id}: {worker.status}")
    print(f"  Completed: {worker.jobs_completed}")
    print(f"  Failed: {worker.jobs_failed}")
    print(f"  Uptime: {worker.uptime}s")

# Scale workers
await job_service.scale_workers(8)  # Scale to 8 workers

# Stop workers gracefully
await job_service.stop_workers(graceful=True)
```

### Metrics

```python
metrics = await job_service.get_metrics()

print("Queue Metrics:")
print(f"  Pending: {metrics['queue']['pending']}")
print(f"  Running: {metrics['queue']['running']}")
print(f"  Completed: {metrics['queue']['completed']}")
print(f"  Dead Letter: {metrics['queue']['dead_letter']}")

print("Worker Metrics:")
print(f"  Total: {metrics['workers']['total']}")
print(f"  Idle: {metrics['workers']['idle']}")
print(f"  Busy: {metrics['workers']['busy']}")
print(f"  Healthy: {metrics['workers']['healthy']}")
```

## Configuration

### Environment Variables

```bash
# Redis URL
export REDIS_URL="redis://localhost:6379/0"

# Worker count (default: CPU count)
export JOB_WORKER_COUNT=4
```

### Programmatic Configuration

```python
from researcharr.core.jobs import JobService
from researcharr.core.jobs.redis_queue import RedisJobQueue
from researcharr.core.jobs.async_worker import AsyncWorkerPool

# Custom queue configuration
queue = RedisJobQueue(
    redis_url="redis://localhost:6379/0",
    key_prefix="myapp:jobs:",
    max_dead_letters=5000,
)

# Custom worker pool
workers = AsyncWorkerPool(queue=queue)

# Create service with custom components
service = JobService(
    queue=queue,
    worker_pool=workers,
    event_bus=my_event_bus,  # Optional
)
```

## Integration with Existing Code

### Wrapping Existing Functions

```python
# Existing sync function
def process_backup(backup_id):
    # ... existing code ...
    return result

# Async wrapper for job handler
async def process_backup_job(job: JobDefinition, progress_callback):
    backup_id = job.args[0]
    
    # Run sync code in thread pool if needed
    result = await asyncio.to_thread(process_backup, backup_id)
    
    return result

job_service.register_handler("process_backup", process_backup_job)
```

### Integration with APScheduler

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Schedule job submissions
async def submit_daily_backup():
    await job_service.submit_job(
        "process_backup",
        args=(datetime.now().date(),),
        priority=JobPriority.NORMAL,
    )

scheduler.add_job(
    submit_daily_backup,
    trigger="cron",
    hour=2,
    minute=0,
)

scheduler.start()
```

## Best Practices

1. **Handler Design**
   - Keep handlers async
   - Use progress callbacks for long tasks
   - Return serializable results (JSON-compatible)
   - Handle errors gracefully

2. **Resource Management**
   - Start appropriate number of workers for workload
   - Monitor worker health regularly
   - Scale workers based on queue depth

3. **Error Handling**
   - Set appropriate max_retries for task types
   - Monitor dead letter queue
   - Implement alerting for critical failures

4. **Performance**
   - Use priorities to ensure critical tasks run first
   - Batch similar jobs when possible
   - Monitor Redis memory usage
   - Use timeouts to prevent stuck jobs

5. **Monitoring**
   - Check metrics regularly
   - Set up alerts for dead letter queue growth
   - Monitor worker health
   - Track job throughput and latency

## Troubleshooting

### Jobs Not Processing

```python
# Check workers are running
workers = await job_service.get_workers()
print(f"Active workers: {len(workers)}")

# Check queue has jobs
metrics = await job_service.get_metrics()
print(f"Pending jobs: {metrics['queue']['pending']}")

# Check handler is registered
print(f"Registered handlers: {job_service._workers.handlers.keys()}")
```

### Jobs Failing Repeatedly

```python
# Check dead letter queue
dead_letters = await job_service.get_dead_letters()
for job in dead_letters:
    # Get error from Redis
    error = await job_service._queue._redis.hget(
        job_service._queue._key("error"),
        str(job.id)
    )
    print(f"Job {job.id} error: {error}")
```

### Redis Connection Issues

```python
# Test Redis connection
import redis.asyncio as redis

try:
    r = redis.from_url("redis://localhost:6379/0")
    await r.ping()
    print("Redis connected")
except Exception as e:
    print(f"Redis error: {e}")
```

## Next Steps

- [Architecture Documentation](../docs/architecture/JOB_QUEUE_DESIGN.md)
- [API Reference](../docs/api/jobs.md) (TODO)
- [Database Schema](../docs/database/jobs.md) (TODO)
- [Metrics Documentation](../docs/monitoring/jobs.md) (TODO)
