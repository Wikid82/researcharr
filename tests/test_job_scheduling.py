from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest

from researcharr.core.jobs import JobService, JobPriority, JobStatus


@pytest.mark.asyncio
async def test_immediate_priority_order(redis_url="redis://localhost:6379/16"):
    svc = JobService(redis_url=redis_url)
    await svc.initialize()

    # Register trivial handlers
    async def handler(job, progress):
        return job.priority.value

    svc.register_handler("test.priority", handler)

    # Submit low then high priority sequentially
    j_low = await svc.submit_job("test.priority", priority=JobPriority.LOW)
    j_high = await svc.submit_job("test.priority", priority=JobPriority.HIGH)

    await svc.start_workers(count=1)

    # Wait for both to complete
    for _ in range(100):
        s_low = await svc.get_job_status(j_low)
        s_high = await svc.get_job_status(j_high)
        if s_low == JobStatus.COMPLETED and s_high == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    # Retrieve results
    r_low = await svc.get_job_result(j_low)
    r_high = await svc.get_job_result(j_high)
    assert r_low and r_high
    # High priority should have run first => worker's first completion should match high priority value
    # We approximate by duration ordering (high priority should have earlier completion time)
    assert r_high.completed_at <= r_low.completed_at

    await svc.shutdown()


@pytest.mark.asyncio
async def test_future_scheduling(redis_url="redis://localhost:6379/16"):
    svc = JobService(redis_url=redis_url)
    await svc.initialize()

    ran = []

    async def handler(job, progress):
        ran.append(job.id)
        return "ok"

    svc.register_handler("test.sched", handler)

    future_time = datetime.now(UTC) + timedelta(seconds=1.0)
    j_future = await svc.submit_job("test.sched", scheduled_at=future_time)
    j_now = await svc.submit_job("test.sched")

    await svc.start_workers(count=1)

    # Poll for immediate job completion
    for _ in range(100):
        s_now = await svc.get_job_status(j_now)
        if s_now == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)
    assert await svc.get_job_status(j_now) == JobStatus.COMPLETED
    # Future job should not have run yet
    assert await svc.get_job_status(j_future) in (JobStatus.PENDING, JobStatus.RETRYING)

    # Wait for future job
    for _ in range(100):
        s_future = await svc.get_job_status(j_future)
        if s_future == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)
    assert await svc.get_job_status(j_future) == JobStatus.COMPLETED

    # Order: j_now should complete before j_future
    r_now = await svc.get_job_result(j_now)
    r_future = await svc.get_job_result(j_future)
    assert r_now and r_future
    assert r_now.completed_at <= r_future.completed_at

    await svc.shutdown()
