"""Example: Job Queue with EventBus Integration.

This example demonstrates how to use the job queue system with the EventBus
to monitor job lifecycle events in real-time.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from researcharr.core import JobService, get_event_bus
from researcharr.core.events import Event, Events
from researcharr.core.jobs import JobDefinition, JobPriority, JobStatus


# Example job handlers
async def process_video(job: JobDefinition, progress):
    """Example video processing job."""
    print(f"  [Handler] Processing video: {job.args[0]}")
    await progress(0, 100, "Starting video processing")

    for i in range(1, 6):
        await asyncio.sleep(0.5)
        await progress(i * 20, 100, f"Processing frame {i * 20}%")

    await progress(100, 100, "Processing complete")
    return {"filename": job.args[0], "frames_processed": 100}


async def generate_report(job: JobDefinition, progress):
    """Example report generation job."""
    report_type = job.kwargs.get("report_type", "summary")
    print(f"  [Handler] Generating {report_type} report")

    await asyncio.sleep(1.0)
    return {"report_type": report_type, "status": "generated"}


async def failing_job(job: JobDefinition, progress):
    """Example job that fails."""
    print("  [Handler] This job will fail...")
    await asyncio.sleep(0.5)
    raise ValueError("Simulated failure")


# Event handlers
def on_job_submitted(event: Event):
    """Handle job submission events."""
    job_id = event.data.get("job_id")
    handler = event.data.get("handler")
    priority = event.data.get("priority")
    print(f"📥 JOB SUBMITTED: {handler} (ID: {job_id[:8]}..., Priority: {priority})")


def on_job_started(event: Event):
    """Handle job started events."""
    job_id = event.data.get("job_id")
    handler = event.data.get("handler")
    print(f"▶️  JOB STARTED: {handler} (ID: {job_id[:8]}...)")


def on_job_progress(event: Event):
    """Handle job progress events."""
    job_id = event.data.get("job_id")
    current = event.data.get("current", 0)
    total = event.data.get("total", 100)
    message = event.data.get("message", "")
    percentage = (current / total * 100) if total > 0 else 0
    print(f"⏳ JOB PROGRESS: ID {job_id[:8]}... - {percentage:.0f}% - {message}")


def on_job_completed(event: Event):
    """Handle job completion events."""
    job_id = event.data.get("job_id")
    handler = event.data.get("handler")
    result = event.data.get("result")
    print(f"✅ JOB COMPLETED: {handler} (ID: {job_id[:8]}...)")
    if result:
        print(f"   Result: {result}")


def on_job_failed(event: Event):
    """Handle job failure events."""
    job_id = event.data.get("job_id")
    handler = event.data.get("handler")
    error = event.data.get("error")
    retry_count = event.data.get("retry_count", 0)
    print(f"❌ JOB FAILED: {handler} (ID: {job_id[:8]}..., Retry: {retry_count})")
    print(f"   Error: {error}")


def on_job_cancelled(event: Event):
    """Handle job cancellation events."""
    job_id = event.data.get("job_id")
    print(f"🚫 JOB CANCELLED: {job_id[:8]}...")


def on_workers_started(event: Event):
    """Handle worker pool start events."""
    count = event.data.get("count")
    print(f"🚀 WORKERS STARTED: {count} workers")


def on_workers_scaled(event: Event):
    """Handle worker pool scaling events."""
    old = event.data.get("old_count")
    new = event.data.get("new_count")
    print(f"📊 WORKERS SCALED: {old} → {new}")


async def main():
    """Run the example."""
    print("=" * 70)
    print("Job Queue + EventBus Integration Example")
    print("=" * 70)
    print()

    # Get event bus and subscribe to all job events
    event_bus = get_event_bus()

    print("📡 Subscribing to job events...")
    event_bus.subscribe(Events.JOB_SUBMITTED, on_job_submitted)
    event_bus.subscribe(Events.JOB_STARTED, on_job_started)
    event_bus.subscribe(Events.JOB_PROGRESS, on_job_progress)
    event_bus.subscribe(Events.JOB_COMPLETED, on_job_completed)
    event_bus.subscribe(Events.JOB_FAILED, on_job_failed)
    event_bus.subscribe(Events.JOB_CANCELLED, on_job_cancelled)
    event_bus.subscribe(Events.JOB_SERVICE_WORKERS_STARTED, on_workers_started)
    event_bus.subscribe(Events.JOB_SERVICE_WORKERS_SCALED, on_workers_scaled)
    print()

    # Create job service with event bus
    service = JobService(
        redis_url="redis://localhost:6379/0",
        event_bus=event_bus,
    )
    await service.initialize()

    # Register handlers
    service.register_handler("process_video", process_video)
    service.register_handler("generate_report", generate_report)
    service.register_handler("failing_job", failing_job)

    # Start workers
    print("🔧 Initializing job service...")
    await service.start_workers(count=2)
    print()

    # Submit various jobs
    print("📝 Submitting jobs...")
    print()

    # Job 1: Video processing
    job1_id = await service.submit_job(
        "process_video",
        args=("movie.mp4",),
        priority=JobPriority.HIGH,
    )

    # Job 2: Report generation
    job2_id = await service.submit_job(
        "generate_report",
        kwargs={"report_type": "analytics"},
        priority=JobPriority.NORMAL,
    )

    # Job 3: Failing job (will retry)
    job3_id = await service.submit_job(
        "failing_job",
        max_retries=2,
        retry_delay=1.0,
    )

    # Wait for jobs to complete
    print()
    print("⏱️  Waiting for jobs to complete...")
    print()

    # Poll for completion
    for _ in range(30):  # Max 30 seconds
        await asyncio.sleep(1.0)

        # Check if all jobs are done
        status1 = await service.get_job_status(job1_id)
        status2 = await service.get_job_status(job2_id)
        status3 = await service.get_job_status(job3_id)

        if all(
            s in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.DEAD_LETTER]
            for s in [status1, status2, status3]
        ):
            break

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    # Get final status for all jobs
    for job_id, name in [
        (job1_id, "Video Processing"),
        (job2_id, "Report Generation"),
        (job3_id, "Failing Job"),
    ]:
        status = await service.get_job_status(job_id)
        result = await service.get_job_result(job_id)

        print(f"Job: {name}")
        print(f"  ID: {job_id}")
        print(f"  Status: {status}")
        if result:
            print(
                f"  Result: {result.result if result.status == JobStatus.COMPLETED else result.error}"
            )
        print()

    # Show metrics
    metrics = await service.get_metrics()
    print("Queue Metrics:")
    print(f"  Pending: {metrics['queue']['pending']}")
    print(f"  Running: {metrics['queue']['running']}")
    print(f"  Completed: {metrics['queue']['completed']}")
    print(f"  Failed: {metrics['queue']['failed']}")
    print()

    print("Worker Metrics:")
    print(f"  Total: {metrics['workers']['total']}")
    print(f"  Healthy: {metrics['workers']['healthy']}")
    print(f"  Jobs Completed: {metrics['workers']['total_jobs_completed']}")
    print(f"  Jobs Failed: {metrics['workers']['total_jobs_failed']}")
    print()

    # Cleanup
    print("🧹 Cleaning up...")
    await service.shutdown(graceful=True)
    print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
