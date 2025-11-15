"""Tests for job queue system."""

from __future__ import annotations

import time

import os
import uuid
from datetime import UTC, datetime

import pytest

from researcharr.core.jobs import (
    JobDefinition,
    JobPriority,
    JobResult,
    JobService,
    JobStatus,
)
from researcharr.core.jobs.threaded_worker import ThreadedWorkerPool
from researcharr.core.jobs.redis_queue import RedisJobQueue


# Test fixtures
@pytest.fixture
def redis_url():
    """Get Redis URL from environment or use default."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/15")  # Use DB 15 for tests


@pytest.fixture
def unique_prefix():
    """Generate unique key prefix for each test to prevent cross-contamination."""
    return f"test:jobs:{uuid.uuid4().hex}:"


@pytest.fixture
def redis_queue(redis_url, unique_prefix):
    """Create and initialize a Redis queue for testing."""
    queue = RedisJobQueue(redis_url=redis_url, key_prefix=unique_prefix)
    queue.initialize()
    yield queue
    # Cleanup - purge all test jobs
    queue.purge()
    queue.shutdown()


@pytest.fixture
def worker_pool(redis_queue):
    """Create a worker pool for testing."""
    pool = ThreadedWorkerPool(queue=redis_queue)
    yield pool
    pool.stop(graceful=False)


@pytest.fixture
def job_service(redis_url, unique_prefix):
    """Create a job service for testing."""
    # Create queue with unique prefix to avoid test pollution
    queue = RedisJobQueue(redis_url=redis_url, key_prefix=unique_prefix)
    queue.initialize()

    # Create service with the queue
    service = JobService(queue=queue)
    service.initialize()
    yield service
    service.purge_jobs()  # Cleanup
    service.shutdown()


# Test handlers
def simple_handler(job: JobDefinition, progress_callback):
    """Simple test handler that returns args."""
    time.sleep(0.1)  # Simulate work
    return {"args": job.args, "kwargs": job.kwargs}


def failing_handler(job: JobDefinition, progress_callback):
    """Handler that always fails."""
    raise ValueError("Test error")


def slow_handler(job: JobDefinition, progress_callback):
    """Handler that takes a while."""
    time.sleep(2.0)
    return "completed"


def progress_handler(job: JobDefinition, progress_callback):
    """Handler that reports progress."""
    for i in range(5):
        progress_callback(i, 5, f"Step {i}")
        time.sleep(0.1)
    return "done"


# Unit tests for JobDefinition
class TestJobDefinition:
    """Test JobDefinition type."""

    def test_create_job(self):
        """Test creating a job definition."""
        job = JobDefinition(
            handler="test.handler",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            priority=JobPriority.HIGH,
        )

        assert job.handler == "test.handler"
        assert job.args == (1, 2, 3)
        assert job.kwargs == {"key": "value"}
        assert job.priority == JobPriority.HIGH
        assert job.max_retries == 3
        assert job.id is not None

    def test_job_validation(self):
        """Test job validation."""
        with pytest.raises(ValueError, match="handler must be specified"):
            JobDefinition(handler="")

        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            JobDefinition(handler="test", max_retries=-1)

    def test_job_serialization(self):
        """Test job serialization/deserialization."""
        job = JobDefinition(
            handler="test.handler",
            args=(1, 2),
            kwargs={"key": "value"},
        )

        # To dict
        job_dict = job.to_dict()
        assert job_dict["handler"] == "test.handler"
        assert job_dict["args"] == (1, 2)  # Tuples preserved in to_dict()

        # From dict
        job2 = JobDefinition.from_dict(job_dict)
        assert job2.id == job.id
        assert job2.handler == job.handler
        assert job2.args == (1, 2)  # Converted back to tuple

        # To/from JSON
        json_str = job.to_json()
        job3 = JobDefinition.from_json(json_str)
        assert job3.id == job.id
        assert job3.handler == job.handler


# Integration tests with Redis
class TestRedisQueue:
    """Test Redis queue implementation."""

    def test_submit_and_get_job(self, redis_queue):
        """Test submitting and retrieving a job."""
        job = JobDefinition(
            handler="test.handler",
            args=(123,),
            priority=JobPriority.NORMAL,
        )

        # Submit
        job_id = redis_queue.submit(job)
        assert job_id == job.id

        # Get status
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.PENDING

        # Get next job
        retrieved = redis_queue.get_next("worker-1")
        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.handler == job.handler

        # Status should be RUNNING now
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.RUNNING

    def test_job_priority(self, redis_queue):
        """Test priority queue ordering."""
        # Submit jobs with different priorities
        low_job = JobDefinition(handler="test", priority=JobPriority.LOW)
        normal_job = JobDefinition(handler="test", priority=JobPriority.NORMAL)
        high_job = JobDefinition(handler="test", priority=JobPriority.HIGH)

        redis_queue.submit(low_job)
        redis_queue.submit(normal_job)
        redis_queue.submit(high_job)

        # Should get high priority first
        job1 = redis_queue.get_next("worker-1")
        assert job1.id == high_job.id

        # Then normal
        job2 = redis_queue.get_next("worker-1")
        assert job2.id == normal_job.id

        # Then low
        job3 = redis_queue.get_next("worker-1")
        assert job3.id == low_job.id

    def test_complete_job(self, redis_queue):
        """Test completing a job."""
        job = JobDefinition(handler="test.handler")
        job_id = redis_queue.submit(job)

        # Get and complete
        redis_queue.get_next("worker-1")

        result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            result={"output": "success"},
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        redis_queue.complete(job_id, result)

        # Check status
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.COMPLETED

        # Get result
        retrieved_result = redis_queue.get_result(job_id)
        assert retrieved_result is not None
        assert retrieved_result.status == JobStatus.COMPLETED

    def test_fail_and_retry(self, redis_queue):
        """Test job failure and retry."""
        job = JobDefinition(
            handler="test.handler",
            max_retries=2,
            retry_delay=0.1,
        )
        job_id = redis_queue.submit(job)

        # Get job
        redis_queue.get_next("worker-1")

        # Fail with retry
        redis_queue.fail(job_id, "Test error", retry=True)

        # Status should be RETRYING
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.RETRYING

        # Should be able to get it again after delay
        time.sleep(0.2)
        retried_job = redis_queue.get_next("worker-1")
        assert retried_job is not None
        assert retried_job.id == job_id

    def test_dead_letter_queue(self, redis_queue):
        """Test dead letter queue for exhausted retries."""
        job = JobDefinition(
            handler="test.handler",
            max_retries=1,
        )
        job_id = redis_queue.submit(job)

        # Fail twice (exceeds max_retries)
        redis_queue.get_next("worker-1")
        redis_queue.fail(job_id, "Error 1", retry=True)

        time.sleep(0.1)
        redis_queue.get_next("worker-1")
        redis_queue.fail(job_id, "Error 2", retry=True)

        # Should be in dead letter queue
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.DEAD_LETTER

        # Get dead letters
        dead_letters = redis_queue.get_dead_letters()
        assert len(dead_letters) >= 1
        assert any(j.id == job_id for j in dead_letters)

    def test_requeue_dead_letter(self, redis_queue):
        """Test requeuing a dead letter job."""
        job = JobDefinition(handler="test.handler", max_retries=1)
        job_id = redis_queue.submit(job)

        # Move to dead letter
        redis_queue.get_next("worker-1")
        redis_queue.fail(job_id, "Error 1", retry=True)
        time.sleep(0.1)
        redis_queue.get_next("worker-1")
        redis_queue.fail(job_id, "Error 2", retry=True)

        assert redis_queue.get_status(job_id) == JobStatus.DEAD_LETTER

        # Requeue
        requeued = redis_queue.requeue_dead_letter(job_id)
        assert requeued is True

        # Should be pending again
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.PENDING

    def test_cancel_job(self, redis_queue):
        """Test cancelling a pending job."""
        job = JobDefinition(handler="test.handler")
        job_id = redis_queue.submit(job)

        # Cancel
        cancelled = redis_queue.cancel(job_id)
        assert cancelled is True

        # Status should be cancelled
        status = redis_queue.get_status(job_id)
        assert status == JobStatus.CANCELLED

        # Should not get this job
        next_job = redis_queue.get_next("worker-1")
        assert next_job is None

    def test_list_jobs(self, redis_queue):
        """Test listing jobs."""
        # Submit multiple jobs
        jobs = [JobDefinition(handler=f"test.handler{i}") for i in range(5)]
        for job in jobs:
            redis_queue.submit(job)

        # List all
        all_jobs = redis_queue.list_jobs()
        assert len(all_jobs) >= 5

        # List by status
        pending_jobs = redis_queue.list_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) >= 5

    def test_metrics(self, redis_queue):
        """Test queue metrics."""
        # Submit some jobs
        job1 = JobDefinition(handler="test.handler1")
        job2 = JobDefinition(handler="test.handler2")

        redis_queue.submit(job1)
        redis_queue.submit(job2)

        metrics = redis_queue.get_metrics()

        assert "pending" in metrics
        assert "running" in metrics
        assert "completed" in metrics
        assert metrics["pending"] >= 2


class TestJobService:
    """Test JobService integration."""

    def test_submit_and_execute_job(self, job_service):
        """Test end-to-end job submission and execution."""
        # Register handler
        job_service.register_handler("simple_test", simple_handler)

        # Start workers
        job_service.start_workers(count=1)

        # Submit job
        job_id = job_service.submit_job(
            "simple_test",
            args=(1, 2, 3),
            kwargs={"key": "value"},
        )

        # Wait for completion
        for _ in range(50):  # Max 5 seconds
            status = job_service.get_job_status(job_id)
            if status == JobStatus.COMPLETED:
                break
            time.sleep(0.1)

        # Check result
        result = job_service.get_job_result(job_id)
        assert result is not None
        assert result.status == JobStatus.COMPLETED
        assert result.result["args"] == [1, 2, 3]
        assert result.result["kwargs"] == {"key": "value"}

    def test_failing_job_retry(self, job_service):
        """Test that failing jobs are retried."""
        job_service.register_handler("failing_test", failing_handler)
        job_service.start_workers(count=1)

        job_id = job_service.submit_job(
            "failing_test",
            max_retries=2,
            retry_delay=0.1,
        )

        # Wait for job to fail completely
        for _ in range(50):
            status = job_service.get_job_status(job_id)
            if status == JobStatus.DEAD_LETTER:
                break
            time.sleep(0.1)

        # Should be in dead letter queue
        status = job_service.get_job_status(job_id)
        assert status == JobStatus.DEAD_LETTER

        dead_letters = job_service.get_dead_letters()
        assert len(dead_letters) >= 1

    def test_get_metrics(self, job_service):
        """Test getting service metrics."""
        job_service.start_workers(count=2)

        metrics = job_service.get_metrics()

        assert "queue" in metrics
        assert "workers" in metrics
        assert metrics["workers"]["total"] == 2

    def test_scale_workers(self, job_service):
        """Test scaling workers."""
        job_service.start_workers(count=2)

        workers = job_service.get_workers()
        assert len(workers) == 2

        # Scale up
        job_service.scale_workers(4)
        workers = job_service.get_workers()
        assert len(workers) == 4

        # Scale down
        job_service.scale_workers(1)
        workers = job_service.get_workers()
        assert len(workers) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
