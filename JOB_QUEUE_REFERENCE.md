# Job Queue System - Quick Reference

## Import

```python
from researcharr.core import (
    JobService, JobPriority, JobStatus,
    JobDefinition, JobResult
)
```

## Setup (One-time)

```python
# Initialize service
service = JobService(redis_url="redis://localhost:6379/0")
await service.initialize()

# Register handlers
async def my_handler(job, progress):
    await progress(0, 100, "Starting")
    # ... do work ...
    await progress(100, 100, "Done")
    return result

service.register_handler("my_handler", my_handler)

# Start workers (default: CPU count)
await service.start_workers()
```

## Submit Jobs

```python
# Basic
job_id = await service.submit_job("my_handler")

# With arguments
job_id = await service.submit_job(
    "my_handler",
    args=(arg1, arg2),
    kwargs={"key": "value"},
)

# With priority
job_id = await service.submit_job(
    "my_handler",
    priority=JobPriority.HIGH,  # CRITICAL, HIGH, NORMAL, LOW
)

# With options
job_id = await service.submit_job(
    "my_handler",
    timeout=300,  # 5 minutes
    max_retries=5,
    retry_delay=2.0,
    retry_backoff=2.0,
)
```

## Track Jobs

```python
# Get status
status = await service.get_job_status(job_id)
# Returns: PENDING, RUNNING, COMPLETED, FAILED, etc.

# Get result
result = await service.get_job_result(job_id)
if result:
    print(f"Output: {result.result}")
    print(f"Duration: {result.duration}s")

# Cancel job
cancelled = await service.cancel_job(job_id)

# List jobs
jobs = await service.list_jobs(status=JobStatus.PENDING, limit=50)

# Dead letters
failed = await service.get_dead_letters()
await service.retry_dead_letter(job_id)
```

## Manage Workers

```python
# Get workers
workers = await service.get_workers()

# Scale workers
await service.scale_workers(8)

# Get metrics
metrics = await service.get_metrics()
print(f"Queue: {metrics['queue']}")
print(f"Workers: {metrics['workers']}")
```

## Handler Pattern

```python
async def handler_template(job: JobDefinition, progress):
    """Job handler template.
    
    Args:
        job: Contains args, kwargs, timeout, etc.
        progress: async callback(current, total, message)
    
    Returns:
        Any JSON-serializable result
    """
    # Get args
    arg1 = job.args[0]
    option = job.kwargs.get("option", "default")
    
    # Report progress
    await progress(0, 100, "Starting")
    
    # Do work
    result = await do_work(arg1, option)
    
    # Report completion
    await progress(100, 100, "Complete")
    
    return result
```

## Priority Levels

```python
JobPriority.CRITICAL  # 30 - highest
JobPriority.HIGH      # 20
JobPriority.NORMAL    # 10 - default
JobPriority.LOW       # 0 - lowest
```

## Job Status

```python
JobStatus.PENDING      # Queued, not started
JobStatus.RUNNING      # Currently executing
JobStatus.COMPLETED    # Successfully finished
JobStatus.FAILED       # Failed after retries
JobStatus.CANCELLED    # Manually cancelled
JobStatus.RETRYING     # Failed, will retry
JobStatus.DEAD_LETTER  # Permanently failed
```

## Integration with APScheduler

```python
from apscheduler.triggers.cron import CronTrigger

async def submit_backup():
    await service.submit_job("backup", priority=JobPriority.HIGH)

scheduler.add_job(
    submit_backup,
    trigger=CronTrigger(hour=2, minute=0),
    id="daily_backup",
)
```

## Integration with Event Bus

```python
async def on_media_added(event):
    media_id = event.data["media_id"]
    await service.submit_job("process_media", args=(media_id,))

event_bus.subscribe("media.added", on_media_added)
```

## Error Handling

```python
try:
    job_id = await service.submit_job("handler")
except ValueError as e:
    print(f"Invalid job: {e}")
except ConnectionError as e:
    print(f"Redis unavailable: {e}")
```

## Cleanup

```python
# Graceful shutdown (waits for jobs)
await service.shutdown(graceful=True)

# Force shutdown
await service.shutdown(graceful=False)

# Purge old jobs
count = await service.purge_jobs(status=JobStatus.COMPLETED)
```

## Environment Variables

```bash
REDIS_URL=redis://localhost:6379/0
JOB_WORKER_COUNT=4
```

## Common Patterns

### Wrap sync function
```python
async def sync_wrapper(job, progress):
    result = await asyncio.to_thread(sync_function, *job.args)
    return result
```

### Batch processing
```python
async def batch_handler(job, progress):
    items = job.args[0]
    for i, item in enumerate(items):
        await process_item(item)
        await progress(i+1, len(items), f"Processed {i+1}/{len(items)}")
    return {"processed": len(items)}
```

### Conditional retry
```python
async def flaky_handler(job, progress):
    try:
        return await unstable_operation()
    except TransientError:
        raise  # Will retry
    except PermanentError:
        return {"error": "permanent", "retry": False}
```

## Monitoring

```python
# Get comprehensive metrics
metrics = await service.get_metrics()

# Queue metrics
print(f"Pending: {metrics['queue']['pending']}")
print(f"Running: {metrics['queue']['running']}")
print(f"Dead letters: {metrics['queue']['dead_letter']}")

# Worker metrics
print(f"Total: {metrics['workers']['total']}")
print(f"Healthy: {metrics['workers']['healthy']}")
print(f"Jobs completed: {metrics['workers']['total_jobs_completed']}")
```

## Troubleshooting

### No workers processing
```python
workers = await service.get_workers()
if len(workers) == 0:
    await service.start_workers()
```

### Too many dead letters
```python
dead = await service.get_dead_letters()
for job in dead:
    print(f"Failed: {job.handler} - {job.id}")
    # Investigate or retry
    await service.retry_dead_letter(job.id)
```

### Redis connection
```bash
# Test Redis
redis-cli ping
# Should return PONG

# Check Redis info
redis-cli info stats
```

## Testing

```python
# tests/test_my_job.py
import pytest
from researcharr.core import JobService

@pytest.mark.asyncio
async def test_my_handler():
    service = JobService(redis_url="redis://localhost:6379/15")
    await service.initialize()
    
    service.register_handler("test", my_handler)
    await service.start_workers(count=1)
    
    job_id = await service.submit_job("test")
    
    # Wait for completion
    for _ in range(50):
        status = await service.get_job_status(job_id)
        if status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    
    result = await service.get_job_result(job_id)
    assert result.status == JobStatus.COMPLETED
    
    await service.shutdown()
```

---

**Full Documentation**: `docs/JOB_QUEUE_QUICKSTART.md`  
**Architecture**: `docs/architecture/JOB_QUEUE_DESIGN.md`  
**Tests**: `tests/test_jobs.py`
