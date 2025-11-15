from __future__ import annotations

import time

from datetime import UTC, datetime, timedelta

import pytest

from researcharr.core.jobs import JobPriority, JobService, JobStatus


def test_immediate_priority_order(redis_url="redis://localhost:6379/10"):
    """Test that jobs with higher priority execute first when all immediate."""
    svc = JobService(redis_url=redis_url)
    svc.initialize()

    # Register trivial handlers
    def handler(job, progress):
        return job.priority.value

    svc.register_handler("test.priority", handler)

    # Submit low then high priority sequentially
    j_low = svc.submit_job("test.priority", priority=JobPriority.LOW)
    j_high = svc.submit_job("test.priority", priority=JobPriority.HIGH)

    svc.start_workers(count=1)

    # Wait for both to complete
    for _ in range(100):
        s_low = svc.get_job_status(j_low)
        s_high = svc.get_job_status(j_high)
        if s_low == JobStatus.COMPLETED and s_high == JobStatus.COMPLETED:
            break
        time.sleep(0.05)

    # Retrieve results
    r_low = svc.get_job_result(j_low)
    r_high = svc.get_job_result(j_high)
    assert r_low and r_high
    # High priority should have run first => worker's first completion should match high priority value
    # We approximate by duration ordering (high priority should have earlier completion time)
    assert r_high.completed_at <= r_low.completed_at

    svc.shutdown()


def test_future_scheduling(redis_url="redis://localhost:6379/11"):
    svc = JobService(redis_url=redis_url)
    svc.initialize()

    ran = []

    def handler(job, progress):
        ran.append(job.id)
        return "ok"

    svc.register_handler("test.sched", handler)

    future_time = datetime.now(UTC) + timedelta(seconds=1.0)
    j_future = svc.submit_job("test.sched", scheduled_at=future_time)
    j_now = svc.submit_job("test.sched")

    svc.start_workers(count=1)

    # Poll for immediate job completion
    for _ in range(100):
        s_now = svc.get_job_status(j_now)
        if s_now == JobStatus.COMPLETED:
            break
        time.sleep(0.05)
    assert svc.get_job_status(j_now) == JobStatus.COMPLETED
    # Future job should not have run yet
    assert svc.get_job_status(j_future) in (JobStatus.PENDING, JobStatus.RETRYING)

    # Wait for future job
    for _ in range(100):
        s_future = svc.get_job_status(j_future)
        if s_future == JobStatus.COMPLETED:
            break
        time.sleep(0.05)
    assert svc.get_job_status(j_future) == JobStatus.COMPLETED

    # Order: j_now should complete before j_future
    r_now = svc.get_job_result(j_now)
    r_future = svc.get_job_result(j_future)
    assert r_now and r_future
    assert r_now.completed_at <= r_future.completed_at

    svc.shutdown()
