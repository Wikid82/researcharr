"""Tests for database health monitoring scheduler service."""

from datetime import datetime
from unittest.mock import Mock, patch

from researcharr.compat import UTC
from researcharr.scheduling.database_scheduler import DatabaseSchedulerService


def test_database_scheduler_initialization():
    """Test DatabaseSchedulerService initialization."""

    scheduler = Mock()
    config = {"database": {"monitoring": {"enabled": True}}}

    service = DatabaseSchedulerService(scheduler, config)

    assert service._scheduler == scheduler
    assert service._config == config


def test_database_scheduler_setup_enabled():
    """Test database scheduler setup with monitoring enabled."""

    scheduler = Mock()
    config = {
        "database": {
            "monitoring": {
                "enabled": True,
                "health_check_interval_minutes": 10,
                "integrity_check_interval_hours": 48,
            }
        }
    }

    service = DatabaseSchedulerService(scheduler, config)
    service.setup()

    # Should add both health check and integrity check jobs
    assert scheduler.add_job.call_count == 2
    calls = scheduler.add_job.call_args_list
    job_names = [call[1]["name"] for call in calls]
    assert "Database Health Check" in job_names
    assert "Database Integrity Check" in job_names


def test_database_scheduler_setup_disabled():
    """Test database scheduler setup with monitoring disabled."""

    scheduler = Mock()
    config = {"database": {"monitoring": {"enabled": False}}}

    service = DatabaseSchedulerService(scheduler, config)
    service.setup()

    # Should not add any jobs
    scheduler.add_job.assert_not_called()


def test_database_scheduler_setup_no_scheduler():
    """Test database scheduler setup with no scheduler."""

    config = {"database": {"monitoring": {"enabled": True}}}

    service = DatabaseSchedulerService(None, config)
    service.setup()

    # Should handle gracefully (no errors)


def test_database_scheduler_remove_jobs():
    """Test removing scheduled database health check jobs."""

    scheduler = Mock()
    scheduler.get_job.return_value = Mock()

    service = DatabaseSchedulerService(scheduler)
    service.remove_jobs()

    # Should attempt to remove both jobs
    assert scheduler.get_job.call_count == 2
    assert scheduler.remove_job.call_count == 2


def test_database_scheduler_remove_jobs_not_found():
    """Test removing jobs when they don't exist."""

    scheduler = Mock()
    scheduler.get_job.return_value = None

    service = DatabaseSchedulerService(scheduler)
    service.remove_jobs()

    # Should not raise errors
    scheduler.remove_job.assert_not_called()


def test_database_scheduler_trigger_health_check():
    """Test triggering health check manually."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.check_database_health.return_value = {"status": "ok"}
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        result = service.trigger_health_check_now()

        assert result is True
        mock_monitor.check_database_health.assert_called_once()


def test_database_scheduler_trigger_integrity_check():
    """Test triggering integrity check manually."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.force_integrity_check.return_value = {
            "checked": True,
            "status": "ok",
        }
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        result = service.trigger_integrity_check_now()

        assert result is True
        mock_monitor.force_integrity_check.assert_called_once()


def test_database_scheduler_get_next_health_check_time():
    """Test getting next health check time."""
    scheduler = Mock()
    job = Mock()
    job.next_run_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    scheduler.get_job.return_value = job

    service = DatabaseSchedulerService(scheduler)
    next_time = service.get_next_health_check_time()

    assert next_time == "2024-01-01T12:00:00+00:00"


def test_database_scheduler_get_next_integrity_check_time():
    """Test getting next integrity check time."""
    scheduler = Mock()
    job = Mock()
    job.next_run_time = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
    scheduler.get_job.return_value = job

    service = DatabaseSchedulerService(scheduler)
    next_time = service.get_next_integrity_check_time()

    assert next_time == "2024-01-02T00:00:00+00:00"


def test_database_scheduler_get_next_time_no_job():
    """Test getting next time when job doesn't exist."""

    scheduler = Mock()
    scheduler.get_job.return_value = None

    service = DatabaseSchedulerService(scheduler)
    next_time = service.get_next_health_check_time()

    assert next_time is None


def test_database_scheduler_get_schedule_info_enabled():
    """Test getting schedule info when monitoring is enabled."""
    scheduler = Mock()
    health_job = Mock()
    health_job.next_run_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    integrity_job = Mock()
    integrity_job.next_run_time = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)

    def get_job(job_id):
        if job_id == "database_health_check":
            return health_job
        elif job_id == "database_integrity_check":
            return integrity_job
        return None

    scheduler.get_job = Mock(side_effect=get_job)

    config = {
        "database": {
            "monitoring": {
                "enabled": True,
                "health_check_interval_minutes": 5,
                "integrity_check_interval_hours": 24,
            }
        }
    }

    service = DatabaseSchedulerService(scheduler, config)
    info = service.get_schedule_info()

    assert info["enabled"] is True
    assert info["health_check_interval_minutes"] == 5
    assert info["integrity_check_interval_hours"] == 24
    assert info["next_health_check"] == "2024-01-01T12:00:00+00:00"
    assert info["next_integrity_check"] == "2024-01-02T00:00:00+00:00"


def test_database_scheduler_get_schedule_info_disabled():
    """Test getting schedule info when monitoring is disabled."""

    scheduler = Mock()
    config = {"database": {"monitoring": {"enabled": False}}}

    service = DatabaseSchedulerService(scheduler, config)
    info = service.get_schedule_info()

    assert info["enabled"] is False


def test_database_scheduler_get_schedule_info_no_scheduler():
    """Test getting schedule info with no scheduler."""

    service = DatabaseSchedulerService(None)
    info = service.get_schedule_info()

    assert info["enabled"] is False
    assert info["next_health_check"] is None
    assert info["next_integrity_check"] is None


def test_database_scheduler_health_check_with_warnings():
    """Test health check that produces warnings."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.check_database_health.return_value = {
            "status": "warning",
            "alerts": [{"level": "warning", "message": "High latency"}],
        }
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        # Should not raise errors
        service._run_health_check()

        mock_monitor.check_database_health.assert_called_once()


def test_database_scheduler_health_check_with_errors():
    """Test health check that produces errors."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.check_database_health.return_value = {
            "status": "error",
            "alerts": [{"level": "error", "message": "Connection failed"}],
        }
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        # Should not raise errors
        service._run_health_check()

        mock_monitor.check_database_health.assert_called_once()


def test_database_scheduler_integrity_check_passed():
    """Test integrity check that passes."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.force_integrity_check.return_value = {
            "checked": True,
            "status": "ok",
            "check_time_ms": 50.5,
        }
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        # Should not raise errors
        service._run_integrity_check()

        mock_monitor.force_integrity_check.assert_called_once()


def test_database_scheduler_integrity_check_failed():
    """Test integrity check that fails."""

    with patch(
        "researcharr.monitoring.database_monitor.get_database_health_monitor"
    ) as mock_get_monitor:
        mock_monitor = Mock()
        mock_monitor.force_integrity_check.return_value = {
            "checked": True,
            "status": "error",
            "result": "corruption detected",
        }
        mock_get_monitor.return_value = mock_monitor

        scheduler = Mock()
        service = DatabaseSchedulerService(scheduler)

        # Should not raise errors
        service._run_integrity_check()

        mock_monitor.force_integrity_check.assert_called_once()
