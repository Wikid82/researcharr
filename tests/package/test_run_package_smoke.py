"""Smoke tests for researcharr.run package module."""

import logging
from unittest.mock import MagicMock, Mock, patch


def test_run_module_imports():
    """Test that run package module imports successfully."""
    import researcharr.run as run

    assert run is not None


def test_run_has_expected_exports():
    """Test that run exports expected functions."""
    import researcharr.run as run

    assert hasattr(run, "run_job")
    assert hasattr(run, "setup_scheduler")
    assert hasattr(run, "load_config")
    assert callable(run.run_job)
    assert callable(run.setup_scheduler)
    assert callable(run.load_config)


def test_load_config_returns_dict():
    """Test load_config returns a dictionary."""
    import researcharr.run as run

    result = run.load_config()
    assert isinstance(result, dict)


def test_get_job_timeout_from_env(monkeypatch):
    """Test _get_job_timeout parses environment variable."""
    import researcharr.run as run

    monkeypatch.setenv("JOB_TIMEOUT", "300")
    timeout = run._get_job_timeout()
    assert timeout == 300.0


def test_get_job_timeout_default():
    """Test _get_job_timeout returns None when not set."""
    import researcharr.run as run

    with patch.dict("os.environ", {}, clear=True):
        timeout = run._get_job_timeout()
        assert timeout is None


def test_get_job_timeout_invalid_returns_none(monkeypatch):
    """Test _get_job_timeout returns None for invalid values."""
    import researcharr.run as run

    monkeypatch.setenv("JOB_TIMEOUT", "invalid")
    timeout = run._get_job_timeout()
    assert timeout is None


def test_run_job_with_script(monkeypatch, caplog):
    """Test run_job executes when script is configured."""
    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "echo test")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")

        with caplog.at_level(logging.INFO):
            run.run_job()

        assert mock_run.called
        assert "Starting scheduled job" in caplog.text


def test_run_job_logs_error_when_no_script(caplog):
    """Test run_job logs error when no script configured."""
    import researcharr.run as run

    with patch.dict("os.environ", {}, clear=True):
        with patch.object(run, "SCRIPT", None):
            with caplog.at_level(logging.ERROR):
                run.run_job()

            assert "No SCRIPT configured" in caplog.text


def test_run_job_handles_timeout_expired(monkeypatch, caplog):
    """Test run_job handles subprocess.TimeoutExpired."""
    import subprocess

    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "sleep 100")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)

        with caplog.at_level(logging.ERROR):
            run.run_job()

        assert "timeout" in caplog.text.lower()


def test_run_job_handles_general_exception(monkeypatch, caplog):
    """Test run_job handles general exceptions."""
    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "echo test")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = OSError("Mock error")

        with caplog.at_level(logging.ERROR):
            run.run_job()

        assert "encountered an error" in caplog.text


def test_setup_scheduler_without_schedule():
    """Test setup_scheduler works when schedule is None."""
    import researcharr.run as run

    with patch.object(run, "schedule", None):
        # Should not raise
        run.setup_scheduler()


def test_setup_scheduler_with_schedule():
    """Test setup_scheduler configures schedule when available."""
    import researcharr.run as run

    mock_schedule = MagicMock()

    with patch.object(run, "schedule", mock_schedule):
        run.setup_scheduler()

        # Verify schedule methods were called
        assert mock_schedule.every.called


def test_run_job_logs_stdout(monkeypatch, caplog):
    """Test run_job logs subprocess stdout."""
    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "echo hello")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="hello world\n", stderr="")

        with caplog.at_level(logging.INFO):
            run.run_job()

        assert "hello world" in caplog.text or "Job stdout" in caplog.text


def test_run_job_logs_stderr(monkeypatch, caplog):
    """Test run_job logs subprocess stderr."""
    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "echo error")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="error message\n")

        with caplog.at_level(logging.INFO):
            run.run_job()

        assert "error message" in caplog.text or "Job stderr" in caplog.text


def test_run_job_with_timeout_parameter(monkeypatch, caplog):
    """Test run_job uses timeout when JOB_TIMEOUT is set."""
    import researcharr.run as run

    monkeypatch.setenv("SCRIPT", "echo test")
    monkeypatch.setenv("JOB_TIMEOUT", "60")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with caplog.at_level(logging.INFO):
            run.run_job()

        # Verify subprocess.run was called with timeout parameter
        call_kwargs = mock_run.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 60.0


def test_main_once_true():
    """Test main function with once=True runs job once."""
    import researcharr.run as run

    with patch.object(run, "run_job") as mock_run_job:
        run.main(once=True)
        mock_run_job.assert_called_once()


def test_main_once_false():
    """Test main function with once=False (breaks after first iteration for test)."""
    import researcharr.run as run

    with patch.object(run, "run_job") as mock_run_job:
        # The implementation breaks after first iteration in test mode
        run.main(once=False)
        mock_run_job.assert_called_once()
