"""Tests for extended CLI commands (health, db, run, config)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_cli_health_command():
    """Test health check command."""
    from researcharr.cli import cmd_health

    args = MagicMock()
    args.json = False

    # The health command will try to import HealthMonitoringService
    # For now, we expect it to fail gracefully
    result = cmd_health(args)

    # Should return error code since HealthMonitoringService doesn't exist yet
    assert result == 1


def test_cli_health_command_json():
    """Test health check command with JSON output."""
    from researcharr.cli import cmd_health

    args = MagicMock()
    args.json = True

    # Mock MonitoringService to return a controlled health status
    with patch("researcharr.cli.MonitoringService") as mock_service:
        mock_instance = MagicMock()
        mock_instance.check_all_health.return_value = {
            "status": "ok",
            "backups": {"status": "ok"},
            "database": {"status": "ok"},
            "alerts": [],
        }
        mock_service.return_value = mock_instance

        result = cmd_health(args)

        # Should return success with ok status
        assert result == 0
        mock_instance.check_all_health.assert_called_once()


def test_cli_db_init_command(tmp_path):
    """Test database init command."""
    from researcharr.cli import cmd_db_init

    db_path = tmp_path / "test.db"

    args = MagicMock()
    args.db_path = str(db_path)

    # Mock at the module level where it's imported
    with patch("researcharr.cli.DatabaseService") as mock_service:
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance

        result = cmd_db_init(args)

        assert result == 0
        mock_instance.init_db.assert_called_once()


def test_cli_db_check_command(tmp_path):
    """Test database integrity check command."""
    from researcharr.cli import cmd_db_check

    db_path = tmp_path / "test.db"
    db_path.write_text("fake db")

    args = MagicMock()
    args.db_path = str(db_path)

    with patch("researcharr.cli.check_db_integrity") as mock_check:
        mock_check.return_value = True

        result = cmd_db_check(args)

        assert result == 0


def test_cli_db_check_command_failure(tmp_path):
    """Test database integrity check command with failure."""
    from researcharr.cli import cmd_db_check

    db_path = tmp_path / "test.db"
    db_path.write_text("fake db")

    args = MagicMock()
    args.db_path = str(db_path)

    with patch("researcharr.cli.check_db_integrity") as mock_check:
        mock_check.return_value = False

        result = cmd_db_check(args)

        assert result == 1


def test_cli_run_job_command():
    """Test run job command."""
    from researcharr.cli import cmd_run_job

    args = MagicMock()

    with patch("researcharr.run.run_job") as mock_run:
        result = cmd_run_job(args)

        assert result == 0
        mock_run.assert_called_once()


def test_cli_config_show_command(tmp_path):
    """Test config show command."""
    from researcharr.cli import cmd_config_show

    config_path = tmp_path / "config.yml"
    config_path.write_text("app:\n  name: test\n")

    args = MagicMock()
    args.config_path = str(config_path)
    args.json = False

    result = cmd_config_show(args)

    assert result == 0


def test_cli_config_show_command_json(tmp_path):
    """Test config show command with JSON output."""
    from researcharr.cli import cmd_config_show

    config_path = tmp_path / "config.yml"
    config_path.write_text("app:\n  name: test\n")

    args = MagicMock()
    args.config_path = str(config_path)
    args.json = True

    result = cmd_config_show(args)

    assert result == 0
