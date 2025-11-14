"""Comprehensive tests for job queue types and data models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from researcharr.core.jobs.types import (
    JobDefinition,
    JobPriority,
    JobProgress,
    JobResult,
    JobStatus,
)


class TestJobStatus:
    """Test JobStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected job statuses are defined."""
        statuses = {s.value for s in JobStatus}
        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses
        assert "retrying" in statuses
        assert "dead_letter" in statuses

    def test_status_from_string(self):
        """Test creating status from string."""
        assert JobStatus("pending") == JobStatus.PENDING
        assert JobStatus("running") == JobStatus.RUNNING
        assert JobStatus("completed") == JobStatus.COMPLETED
        assert JobStatus("failed") == JobStatus.FAILED

    def test_status_str_representation(self):
        """Test string representation."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.COMPLETED.value == "completed"


class TestJobPriority:
    """Test JobPriority enum."""

    def test_all_priorities_defined(self):
        """Test all expected priorities are defined."""
        priorities = {p.name for p in JobPriority}
        assert "LOW" in priorities
        assert "NORMAL" in priorities
        assert "HIGH" in priorities
        assert "CRITICAL" in priorities

    def test_priority_values(self):
        """Test priority numeric values for ordering."""
        assert JobPriority.LOW.value < JobPriority.NORMAL.value
        assert JobPriority.NORMAL.value < JobPriority.HIGH.value
        assert JobPriority.HIGH.value < JobPriority.CRITICAL.value

    def test_priority_ordering(self):
        """Test priorities can be compared."""
        assert JobPriority.LOW < JobPriority.NORMAL
        assert JobPriority.NORMAL < JobPriority.HIGH
        assert JobPriority.HIGH < JobPriority.CRITICAL


class TestJobDefinition:
    """Test JobDefinition data class."""

    def test_create_minimal_job(self):
        """Test creating job with minimal fields."""
        job = JobDefinition(handler="test.handler")
        assert job.handler == "test.handler"
        assert isinstance(job.id, UUID)
        assert job.priority == JobPriority.NORMAL
        assert job.args == ()
        assert job.kwargs == {}
        assert job.max_retries == 3
        assert job.timeout is None
        assert job.scheduled_at is None

    def test_create_job_with_all_fields(self):
        """Test creating job with all fields specified."""
        job_id = uuid4()
        created = datetime.now(UTC)
        scheduled = created + timedelta(hours=1)

        job = JobDefinition(
            handler="backup.create",
            id=job_id,
            args=("arg1", "arg2"),
            kwargs={"key": "value"},
            priority=JobPriority.HIGH,
            max_retries=5,
            timeout=300.0,
            retry_delay=10.0,
            retry_backoff=2.5,
            created_at=created,
            scheduled_at=scheduled,
        )

        assert job.id == job_id
        assert job.handler == "backup.create"
        assert job.args == ("arg1", "arg2")
        assert job.kwargs == {"key": "value"}
        assert job.priority == JobPriority.HIGH
        assert job.max_retries == 5
        assert job.timeout == 300.0
        assert job.retry_delay == 10.0
        assert job.retry_backoff == 2.5
        assert job.created_at == created
        assert job.scheduled_at == scheduled

    def test_job_serialization_minimal(self):
        """Test serialization with minimal fields."""
        job = JobDefinition(handler="test.handler")
        data = job.to_dict()
        assert data["handler"] == "test.handler"
        assert data["priority"] == 10

    def test_job_serialization_complete(self):
        """Test JSON serialization with all fields."""
        scheduled = datetime.now(UTC) + timedelta(hours=2)
        job = JobDefinition(
            handler="backup.restore",
            args=("file.tar.gz",),
            kwargs={"overwrite": True},
            priority=JobPriority.CRITICAL,
            max_retries=1,
            timeout=600.0,
            scheduled_at=scheduled,
        )

        data = job.to_dict()
        assert data["handler"] == "backup.restore"
        assert data["args"] == ("file.tar.gz",)
        assert data["kwargs"] == {"overwrite": True}
        assert data["priority"] == 30  # CRITICAL.value
        assert data["max_retries"] == 1
        assert data["timeout"] == 600.0
        assert data["scheduled_at"] == scheduled.isoformat()

    def test_job_json_roundtrip(self):
        """Test job can be serialized and deserialized."""
        original = JobDefinition(
            handler="test.task",
            args=(1, 2, 3),
            kwargs={"mode": "fast"},
            priority=JobPriority.HIGH,
            timeout=120.0,
        )

        # Serialize to JSON string
        json_str = original.to_json()
        assert isinstance(json_str, str)

        # Deserialize back
        restored = JobDefinition.from_json(json_str)

        assert restored.handler == original.handler
        assert restored.args == original.args
        assert restored.kwargs == original.kwargs
        assert restored.priority == original.priority
        assert restored.timeout == original.timeout
        assert restored.id == original.id

    def test_job_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": str(uuid4()),
            "name": "email_sender",
            "handler": "email.send",
            "args": ["recipient@example.com"],
            "kwargs": {"subject": "Test"},
            "priority": 20,
            "max_retries": 2,
            "timeout": 30.0,
            "created_at": datetime.now(UTC).isoformat(),
            "depends_on": [],
        }

        job = JobDefinition.from_dict(data)
        assert job.handler == "email.send"
        assert job.args == ("recipient@example.com",)
        assert job.kwargs == {"subject": "Test"}
        assert job.priority == JobPriority.HIGH
        assert job.max_retries == 2
        assert job.timeout == 30.0

    def test_job_scheduled_at_serialization(self):
        """Test scheduled_at field serialization."""
        future = datetime.now(UTC) + timedelta(days=1)
        job = JobDefinition(handler="scheduled.task", scheduled_at=future)

        # Check dict representation
        data = job.to_dict()
        assert data["scheduled_at"] == future.isoformat()

        # Check roundtrip
        restored = JobDefinition.from_dict(data)
        assert restored.scheduled_at is not None
        # Allow small time delta due to microsecond precision
        assert abs((restored.scheduled_at - future).total_seconds()) < 0.001


class TestJobResult:
    """Test JobResult data class."""

    def test_create_pending_result(self):
        """Test creating result for pending job."""
        job_id = uuid4()
        result = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            worker_id=None,
        )

        assert result.job_id == job_id
        assert result.status == JobStatus.PENDING
        assert result.worker_id is None
        assert result.result is None
        assert result.error is None
        assert result.attempts == 0

    def test_create_running_result(self):
        """Test creating result for running job."""
        job_id = uuid4()
        started = datetime.now(UTC)

        result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            worker_id="worker-1",
            started_at=started,
        )

        assert result.status == JobStatus.RUNNING
        assert result.worker_id == "worker-1"
        assert result.started_at == started
        assert result.completed_at is None

    def test_create_completed_result(self):
        """Test creating result for completed job."""
        job_id = uuid4()
        started = datetime.now(UTC)
        completed = started + timedelta(seconds=10)

        result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            worker_id="worker-1",
            started_at=started,
            completed_at=completed,
            result={"success": True, "count": 42},
        )

        assert result.status == JobStatus.COMPLETED
        assert result.result == {"success": True, "count": 42}
        assert result.error is None
        assert result.completed_at == completed

    def test_create_failed_result(self):
        """Test creating result for failed job."""
        job_id = uuid4()
        result = JobResult(
            job_id=job_id,
            status=JobStatus.FAILED,
            worker_id="worker-2",
            error="Connection timeout",
            attempts=3,
        )

        assert result.status == JobStatus.FAILED
        assert result.error == "Connection timeout"
        assert result.attempts == 3
        assert result.result is None

    def test_result_duration_calculation(self):
        """Test duration property calculation."""
        started = datetime.now(UTC)
        completed = started + timedelta(seconds=45)

        result = JobResult(
            job_id=uuid4(),
            status=JobStatus.COMPLETED,
            worker_id="worker-1",
            started_at=started,
            completed_at=completed,
        )

        assert 44.9 < result.duration < 45.1

    def test_result_duration_none_when_not_started(self):
        """Test duration is None when job not started."""
        result = JobResult(
            job_id=uuid4(),
            status=JobStatus.PENDING,
            worker_id=None,
        )

        assert result.duration is None

    def test_result_serialization(self):
        """Test result serialization to dict."""
        started = datetime.now(UTC)
        result = JobResult(
            job_id=uuid4(),
            status=JobStatus.COMPLETED,
            worker_id="worker-3",
            started_at=started,
            completed_at=started + timedelta(seconds=5),
            result="done",
            attempts=1,
        )

        data = result.to_dict()
        assert data["status"] == "completed"
        assert data["worker_id"] == "worker-3"
        assert data["result"] == "done"
        assert data["attempts"] == 1
        # duration is a property, not in dict
        assert result.duration is not None

    def test_result_json_roundtrip(self):
        """Test result JSON serialization roundtrip."""
        original = JobResult(
            job_id=uuid4(),
            status=JobStatus.FAILED,
            worker_id="worker-1",
            error="Test error",
            attempts=2,
        )

        json_str = original.to_json()
        restored = JobResult.from_json(json_str)

        assert restored.job_id == original.job_id
        assert restored.status == original.status
        assert restored.worker_id == original.worker_id
        assert restored.error == original.error
        assert restored.attempts == original.attempts

    def test_result_from_dict_with_timestamps(self):
        """Test creating result from dict with ISO timestamps."""
        started = datetime.now(UTC)
        completed = started + timedelta(minutes=1)

        data = {
            "job_id": str(uuid4()),
            "status": "completed",
            "worker_id": "w1",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "result": {"value": 123},
            "attempts": 1,
        }

        result = JobResult.from_dict(data)
        assert result.status == JobStatus.COMPLETED
        assert result.started_at is not None
        assert result.completed_at is not None
        assert abs((result.started_at - started).total_seconds()) < 0.001
        assert result.result == {"value": 123}


class TestJobProgress:
    """Test JobProgress data class."""

    def test_create_progress(self):
        """Test creating progress report."""
        job_id = uuid4()
        progress = JobProgress(
            job_id=job_id,
            current=50,
            total=100,
            message="Processing items",
        )

        assert progress.job_id == job_id
        assert progress.current == 50
        assert progress.total == 100
        assert progress.message == "Processing items"

    def test_create_progress_no_total(self):
        """Test progress without total count."""
        progress = JobProgress(
            job_id=uuid4(),
            current=25,
            message="Still working",
        )

        assert progress.current == 25
        assert progress.total is None
        assert progress.message == "Still working"

    def test_progress_percentage_calculation(self):
        """Test percentage property."""
        progress = JobProgress(
            job_id=uuid4(),
            current=75,
            total=200,
        )

        assert progress.percentage == 37.5

    def test_progress_percentage_no_total(self):
        """Test percentage is None without total."""
        progress = JobProgress(
            job_id=uuid4(),
            current=10,
        )

        assert progress.percentage is None

    def test_progress_percentage_zero_total(self):
        """Test percentage with zero total."""
        progress = JobProgress(
            job_id=uuid4(),
            current=0,
            total=0,
        )

        assert progress.percentage is None  # No total means no percentage

    def test_progress_serialization(self):
        """Test progress serialization."""
        progress = JobProgress(
            job_id=uuid4(),
            current=33,
            total=100,
            message="33% complete",
        )

        data = progress.to_dict()
        assert data["current"] == 33
        assert data["total"] == 100
        assert data["message"] == "33% complete"
        # percentage is a property, not in dict
        assert progress.percentage == 33.0

    def test_progress_json_roundtrip(self):
        """Test progress JSON roundtrip."""
        original = JobProgress(
            job_id=uuid4(),
            current=200,
            total=1000,
            message="Step 2 of 5",
        )

        json_str = original.to_json()
        restored = JobProgress.from_json(json_str)

        assert restored.job_id == original.job_id
        assert restored.current == original.current
        assert restored.total == original.total
        assert restored.message == original.message

    def test_progress_from_dict_minimal(self):
        """Test creating progress from minimal dict."""
        data = {
            "job_id": str(uuid4()),
            "current": 5,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        progress = JobProgress.from_dict(data)
        assert progress.current == 5
        assert progress.total is None
        assert progress.message == ""


class TestJobDefinitionValidation:
    """Test JobDefinition validation and edge cases."""

    def test_empty_handler_name(self):
        """Test that empty handler name is rejected."""
        with pytest.raises(ValueError):
            JobDefinition(handler="")

    def test_negative_max_retries(self):
        """Test that negative max_retries raises error."""
        with pytest.raises(ValueError):
            JobDefinition(handler="test", max_retries=-1)

    def test_negative_timeout(self):
        """Test that negative timeout raises error."""
        with pytest.raises(ValueError):
            JobDefinition(handler="test", timeout=-10.0)

    def test_invalid_priority_string(self):
        """Test handling invalid priority in from_dict."""
        data = {
            "handler": "test",
            "priority": "invalid_priority",
        }

        with pytest.raises((KeyError, ValueError)):
            JobDefinition.from_dict(data)

    def test_scheduled_at_in_past_allowed(self):
        """Test that past scheduled_at is allowed (for re-queuing)."""
        past = datetime.now(UTC) - timedelta(hours=1)
        job = JobDefinition(handler="test", scheduled_at=past)
        assert job.scheduled_at == past


class TestComplexSerialization:
    """Test complex serialization scenarios."""

    def test_job_with_nested_kwargs(self):
        """Test job with complex nested kwargs."""
        job = JobDefinition(
            handler="complex.task",
            kwargs={
                "config": {
                    "nested": {"value": 123},
                    "list": [1, 2, 3],
                },
                "flags": ["a", "b"],
            },
        )

        json_str = job.to_json()
        restored = JobDefinition.from_json(json_str)

        assert restored.kwargs["config"]["nested"]["value"] == 123
        assert restored.kwargs["config"]["list"] == [1, 2, 3]
        assert restored.kwargs["flags"] == ["a", "b"]

    def test_result_with_complex_result_data(self):
        """Test result with complex result data."""
        result = JobResult(
            job_id=uuid4(),
            status=JobStatus.COMPLETED,
            worker_id="w1",
            result={
                "stats": {"count": 100, "success": 95},
                "errors": [{"line": 1, "msg": "warning"}],
            },
        )

        json_str = result.to_json()
        restored = JobResult.from_json(json_str)

        assert restored.result["stats"]["count"] == 100
        assert len(restored.result["errors"]) == 1

    def test_unicode_in_job_data(self):
        """Test unicode strings in job data."""
        job = JobDefinition(
            handler="i18n.task",
            args=("Hello 世界", "Привет"),
            kwargs={"message": "مرحبا"},
        )

        json_str = job.to_json()
        restored = JobDefinition.from_json(json_str)

        assert restored.args[0] == "Hello 世界"
        assert restored.args[1] == "Привет"
        assert restored.kwargs["message"] == "مرحبا"
