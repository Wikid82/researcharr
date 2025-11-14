"""Comprehensive tests for JobService orchestration layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from researcharr.core.jobs.service import JobService
from researcharr.core.jobs.types import JobDefinition, JobPriority, JobResult, JobStatus


@pytest.fixture
def mock_queue():
    """Create a mock job queue."""
    queue = AsyncMock()
    queue.initialize = AsyncMock()
    queue.shutdown = AsyncMock()
    queue.submit = AsyncMock(return_value=uuid4())
    queue.get_status = AsyncMock(return_value=JobStatus.PENDING)
    queue.get_result = AsyncMock(return_value=None)
    queue.cancel = AsyncMock(return_value=True)
    queue.list_jobs = AsyncMock(return_value=[])
    queue.get_dead_letters = AsyncMock(return_value=[])
    queue.requeue_dead_letter = AsyncMock(return_value=True)
    queue.purge = AsyncMock(return_value=0)
    queue.get_metrics = AsyncMock(return_value={})
    return queue


@pytest.fixture
def mock_worker_pool():
    """Create a mock worker pool."""
    pool = AsyncMock()
    pool.start = AsyncMock()
    pool.stop = AsyncMock()
    pool.scale = AsyncMock()
    pool.get_workers = AsyncMock(return_value=[])
    pool.get_worker = AsyncMock(return_value=None)
    pool.restart_worker = AsyncMock(return_value=True)
    pool.heartbeat = AsyncMock()
    pool.get_metrics = AsyncMock(return_value={})
    pool.register_handler = Mock()
    return pool


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
async def job_service(mock_queue, mock_worker_pool):
    """Create a job service with mocked dependencies."""
    service = JobService(
        queue=mock_queue,
        worker_pool=mock_worker_pool,
    )
    await service.initialize()
    yield service
    await service.shutdown()


class TestJobServiceInitialization:
    """Test job service initialization and lifecycle."""

    async def test_service_creation_with_defaults(self):
        """Test creating service with default configuration."""
        with patch("researcharr.core.jobs.service.RedisJobQueue") as mock_redis:
            with patch("researcharr.core.jobs.service.AsyncWorkerPool") as mock_pool:
                mock_queue_instance = AsyncMock()
                mock_redis.return_value = mock_queue_instance

                service = JobService()
                assert service._queue == mock_queue_instance
                mock_redis.assert_called_once()

    async def test_service_creation_with_custom_queue(self, mock_queue):
        """Test creating service with custom queue."""
        service = JobService(queue=mock_queue)
        assert service._queue == mock_queue

    async def test_service_creation_with_event_bus(self, mock_queue, mock_event_bus):
        """Test creating service with event bus."""
        service = JobService(queue=mock_queue, event_bus=mock_event_bus)
        assert service._events == mock_event_bus

    async def test_initialize_initializes_queue(self, mock_queue):
        """Test that initialize() initializes the queue."""
        service = JobService(queue=mock_queue)
        await service.initialize()

        mock_queue.initialize.assert_called_once()

    async def test_initialize_idempotent(self, mock_queue):
        """Test that initialize() can be called multiple times safely."""
        service = JobService(queue=mock_queue)

        await service.initialize()
        await service.initialize()
        await service.initialize()

        # Should only initialize once
        assert mock_queue.initialize.call_count == 1

    async def test_shutdown_stops_workers_first(self, mock_queue, mock_worker_pool):
        """Test that shutdown() stops workers before queue."""
        service = JobService(queue=mock_queue, worker_pool=mock_worker_pool)
        await service.initialize()

        await service.shutdown()

        # Workers should stop before queue shuts down
        mock_worker_pool.stop.assert_called_once()
        mock_queue.shutdown.assert_called_once()

    async def test_shutdown_graceful(self, mock_queue, mock_worker_pool):
        """Test graceful shutdown parameter."""
        service = JobService(queue=mock_queue, worker_pool=mock_worker_pool)
        await service.initialize()

        await service.shutdown(graceful=True)

        mock_worker_pool.stop.assert_called_once_with(graceful=True)
        mock_queue.shutdown.assert_called_once_with(graceful=True)

    async def test_shutdown_force(self, mock_queue, mock_worker_pool):
        """Test force shutdown."""
        service = JobService(queue=mock_queue, worker_pool=mock_worker_pool)
        await service.initialize()

        await service.shutdown(graceful=False)

        mock_worker_pool.stop.assert_called_once_with(graceful=False)

    async def test_shutdown_when_not_initialized(self, mock_queue, mock_worker_pool):
        """Test shutdown when service not initialized does nothing."""
        service = JobService(queue=mock_queue, worker_pool=mock_worker_pool)

        await service.shutdown()

        mock_worker_pool.stop.assert_not_called()
        mock_queue.shutdown.assert_not_called()


class TestJobSubmission:
    """Test job submission functionality."""

    async def test_submit_minimal_job(self, job_service, mock_queue):
        """Test submitting job with minimal parameters."""
        job_id = await job_service.submit_job("test.handler")

        assert job_id is not None
        mock_queue.submit.assert_called_once()

        # Check submitted job
        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.handler == "test.handler"
        assert submitted_job.priority == JobPriority.NORMAL

    async def test_submit_job_with_args(self, job_service, mock_queue):
        """Test submitting job with args and kwargs."""
        await job_service.submit_job(
            "process.data",
            args=("arg1", "arg2"),
            kwargs={"key": "value"},
        )

        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.args == ("arg1", "arg2")
        assert submitted_job.kwargs == {"key": "value"}

    async def test_submit_job_with_priority(self, job_service, mock_queue):
        """Test submitting job with custom priority."""
        await job_service.submit_job(
            "urgent.task",
            priority=JobPriority.CRITICAL,
        )

        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.priority == JobPriority.CRITICAL

    async def test_submit_job_with_timeout(self, job_service, mock_queue):
        """Test submitting job with timeout."""
        await job_service.submit_job(
            "long.task",
            timeout=300.0,
        )

        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.timeout == 300.0

    async def test_submit_job_with_max_retries(self, job_service, mock_queue):
        """Test submitting job with custom max_retries."""
        await job_service.submit_job(
            "flaky.task",
            max_retries=5,
        )

        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.max_retries == 5

    async def test_submit_scheduled_job(self, job_service, mock_queue):
        """Test submitting job with scheduled_at."""
        future_time = datetime.now(UTC) + timedelta(hours=1)

        await job_service.submit_job(
            "scheduled.task",
            scheduled_at=future_time,
        )

        submitted_job = mock_queue.submit.call_args[0][0]
        assert submitted_job.scheduled_at == future_time

    async def test_submit_job_raises_when_not_initialized(self, mock_queue):
        """Test submitting job before initialization raises error."""
        service = JobService(queue=mock_queue)

        with pytest.raises(RuntimeError, match="not initialized"):
            await service.submit_job("test")

    async def test_submit_job_publishes_event(self, mock_queue, mock_worker_pool, mock_event_bus):
        """Test that job submission publishes event."""
        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=mock_event_bus,
        )
        await service.initialize()

        job_id = await service.submit_job("test.handler")

        # Check event was published
        mock_event_bus.publish.assert_called_once()
        event_name, event_data = mock_event_bus.publish.call_args[0]
        assert event_name == "job.submitted"
        assert event_data["handler"] == "test.handler"

    async def test_submit_scheduled_job_publishes_schedule_time(
        self, mock_queue, mock_worker_pool, mock_event_bus
    ):
        """Test scheduled job event includes scheduled_at."""
        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=mock_event_bus,
        )
        await service.initialize()

        future = datetime.now(UTC) + timedelta(hours=2)
        await service.submit_job("test", scheduled_at=future)

        event_data = mock_event_bus.publish.call_args[0][1]
        assert event_data["scheduled_at"] == future.isoformat()


class TestJobQuerying:
    """Test job querying and status functionality."""

    async def test_get_job_status(self, job_service, mock_queue):
        """Test getting job status."""
        job_id = uuid4()
        mock_queue.get_status.return_value = JobStatus.RUNNING

        status = await job_service.get_job_status(job_id)

        assert status == JobStatus.RUNNING
        mock_queue.get_status.assert_called_once_with(job_id)

    async def test_get_job_status_not_found(self, job_service, mock_queue):
        """Test getting status of non-existent job."""
        job_id = uuid4()
        mock_queue.get_status.return_value = None

        status = await job_service.get_job_status(job_id)

        assert status is None

    async def test_get_job_result(self, job_service, mock_queue):
        """Test getting job result."""
        job_id = uuid4()
        expected_result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            worker_id="w1",
            result={"success": True},
        )
        mock_queue.get_result.return_value = expected_result

        result = await job_service.get_job_result(job_id)

        assert result == expected_result
        mock_queue.get_result.assert_called_once_with(job_id)

    async def test_get_job_result_not_finished(self, job_service, mock_queue):
        """Test getting result of unfinished job."""
        job_id = uuid4()
        mock_queue.get_result.return_value = None

        result = await job_service.get_job_result(job_id)

        assert result is None

    async def test_list_jobs_all(self, job_service, mock_queue):
        """Test listing all jobs."""
        expected_jobs = [
            JobDefinition(handler="task1"),
            JobDefinition(handler="task2"),
        ]
        mock_queue.list_jobs.return_value = expected_jobs

        jobs = await job_service.list_jobs()

        assert jobs == expected_jobs
        mock_queue.list_jobs.assert_called_once_with(status=None, limit=100, offset=0)

    async def test_list_jobs_filtered_by_status(self, job_service, mock_queue):
        """Test listing jobs filtered by status."""
        await job_service.list_jobs(status=JobStatus.RUNNING)

        mock_queue.list_jobs.assert_called_once_with(
            status=JobStatus.RUNNING, limit=100, offset=0
        )

    async def test_list_jobs_with_pagination(self, job_service, mock_queue):
        """Test listing jobs with pagination."""
        await job_service.list_jobs(limit=50, offset=100)

        mock_queue.list_jobs.assert_called_once_with(status=None, limit=50, offset=100)


class TestJobCancellation:
    """Test job cancellation functionality."""

    async def test_cancel_job_success(self, job_service, mock_queue):
        """Test successfully cancelling a job."""
        job_id = uuid4()
        mock_queue.cancel.return_value = True

        cancelled = await job_service.cancel_job(job_id)

        assert cancelled is True
        mock_queue.cancel.assert_called_once_with(job_id)

    async def test_cancel_job_failure(self, job_service, mock_queue):
        """Test cancelling already running job."""
        job_id = uuid4()
        mock_queue.cancel.return_value = False

        cancelled = await job_service.cancel_job(job_id)

        assert cancelled is False

    async def test_cancel_job_publishes_event(self, mock_queue, mock_worker_pool, mock_event_bus):
        """Test that successful cancellation publishes event."""
        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=mock_event_bus,
        )
        await service.initialize()

        job_id = uuid4()
        mock_queue.cancel.return_value = True

        await service.cancel_job(job_id)

        mock_event_bus.publish.assert_called_once()
        event_name, event_data = mock_event_bus.publish.call_args[0]
        assert event_name == "job.cancelled"
        assert event_data["job_id"] == str(job_id)

    async def test_cancel_job_no_event_when_failed(
        self, mock_queue, mock_worker_pool, mock_event_bus
    ):
        """Test that failed cancellation doesn't publish event."""
        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=mock_event_bus,
        )
        await service.initialize()

        job_id = uuid4()
        mock_queue.cancel.return_value = False

        await service.cancel_job(job_id)

        # No event published since cancellation failed
        mock_event_bus.publish.assert_not_called()


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    async def test_get_dead_letters(self, job_service, mock_queue):
        """Test getting dead letter jobs."""
        expected_jobs = [
            JobDefinition(handler="failed1"),
            JobDefinition(handler="failed2"),
        ]
        mock_queue.get_dead_letters.return_value = expected_jobs

        jobs = await job_service.get_dead_letters()

        assert jobs == expected_jobs
        mock_queue.get_dead_letters.assert_called_once_with(limit=100)

    async def test_get_dead_letters_with_limit(self, job_service, mock_queue):
        """Test getting dead letters with custom limit."""
        await job_service.get_dead_letters(limit=50)

        mock_queue.get_dead_letters.assert_called_once_with(limit=50)

    async def test_retry_dead_letter_success(self, job_service, mock_queue):
        """Test successfully retrying dead letter job."""
        job_id = uuid4()
        mock_queue.requeue_dead_letter.return_value = True

        requeued = await job_service.retry_dead_letter(job_id)

        assert requeued is True
        mock_queue.requeue_dead_letter.assert_called_once_with(job_id)

    async def test_retry_dead_letter_not_found(self, job_service, mock_queue):
        """Test retrying non-existent dead letter job."""
        job_id = uuid4()
        mock_queue.requeue_dead_letter.return_value = False

        requeued = await job_service.retry_dead_letter(job_id)

        assert requeued is False


class TestWorkerManagement:
    """Test worker pool management functionality."""

    async def test_register_handler(self, job_service, mock_worker_pool):
        """Test registering a job handler."""

        async def test_handler(job, progress):
            return "done"

        job_service.register_handler("test", test_handler)

        mock_worker_pool.register_handler.assert_called_once_with("test", test_handler)

    async def test_start_workers(self, job_service, mock_worker_pool):
        """Test starting worker pool."""
        await job_service.start_workers(count=4)

        mock_worker_pool.start.assert_called_once_with(4)

    async def test_stop_workers_graceful(self, job_service, mock_worker_pool):
        """Test stopping workers gracefully."""
        await job_service.stop_workers(graceful=True)

        mock_worker_pool.stop.assert_called_once_with(graceful=True, timeout=30.0)

    async def test_stop_workers_with_timeout(self, job_service, mock_worker_pool):
        """Test stopping workers with custom timeout."""
        await job_service.stop_workers(graceful=True, timeout=60.0)

        mock_worker_pool.stop.assert_called_once_with(graceful=True, timeout=60.0)

    async def test_scale_workers(self, job_service, mock_worker_pool):
        """Test scaling worker pool."""
        await job_service.scale_workers(8)

        mock_worker_pool.scale.assert_called_once_with(8)

    async def test_get_workers(self, job_service, mock_worker_pool):
        """Test getting worker information."""
        expected_workers = [Mock(id="w1"), Mock(id="w2")]
        mock_worker_pool.get_workers.return_value = expected_workers

        workers = await job_service.get_workers()

        assert workers == expected_workers

    async def test_get_worker(self, job_service, mock_worker_pool):
        """Test getting specific worker information."""
        expected_worker = Mock(id="w1")
        mock_worker_pool.get_worker.return_value = expected_worker

        worker = await job_service.get_worker("w1")

        assert worker == expected_worker
        mock_worker_pool.get_worker.assert_called_once_with("w1")

    async def test_restart_worker(self, job_service, mock_worker_pool):
        """Test restarting a worker."""
        mock_worker_pool.restart_worker.return_value = True

        restarted = await job_service.restart_worker("w1")

        assert restarted is True
        mock_worker_pool.restart_worker.assert_called_once_with("w1")


class TestMetrics:
    """Test metrics collection functionality."""

    async def test_get_metrics_combines_queue_and_worker_metrics(
        self, job_service, mock_queue, mock_worker_pool
    ):
        """Test that get_metrics combines queue and worker metrics."""
        mock_queue.get_metrics.return_value = {
            "pending": 10,
            "running": 5,
            "completed": 100,
        }
        mock_worker_pool.get_metrics.return_value = {
            "total": 4,
            "idle": 2,
            "busy": 2,
        }

        metrics = await job_service.get_metrics()

        assert metrics["queue"]["pending"] == 10
        assert metrics["queue"]["running"] == 5
        assert metrics["queue"]["completed"] == 100
        assert metrics["workers"]["total"] == 4
        assert metrics["workers"]["idle"] == 2
        assert metrics["workers"]["busy"] == 2


class TestEventPublishing:
    """Test event publishing integration."""

    async def test_publish_event_when_bus_present(self, mock_queue, mock_worker_pool):
        """Test that events are published when event bus is configured."""
        mock_event_bus = AsyncMock()

        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=mock_event_bus,
        )
        await service.initialize()

        # Submit a job
        await service.submit_job("test")

        # Event should be published
        mock_event_bus.publish.assert_called_once()

    async def test_no_event_when_bus_not_configured(self, mock_queue, mock_worker_pool):
        """Test that no events published when no event bus."""
        service = JobService(
            queue=mock_queue,
            worker_pool=mock_worker_pool,
            event_bus=None,
        )
        await service.initialize()

        # Submit a job
        await service.submit_job("test")

        # No errors should occur
        mock_queue.submit.assert_called_once()
