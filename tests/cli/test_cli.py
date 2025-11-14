"""Tests for researcharr.cli module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_backups(tmp_path):
    """Create mock backup directory structure."""
    config_dir = tmp_path / "config"
    backups_dir = config_dir / "backups"
    backups_dir.mkdir(parents=True)

    # Create mock backup file
    backup_file = backups_dir / "researcharr-backup-20250110T120000Z.zip"
    backup_file.write_text("mock backup content")

    return config_dir, backups_dir, backup_file


def test_cli_main_no_args(capsys):
    """Test CLI with no arguments shows help."""
    from researcharr.cli import main

    with patch.object(sys, "argv", ["researcharr-cli"]):
        result = main()

    # CLI shows help and returns 1
    assert result == 1
    captured = capsys.readouterr()
    assert "ResearchArr Management CLI" in captured.out


def test_cli_create_command(mock_backups):
    """Test backup create command."""
    from researcharr.cli import cmd_create

    config_dir, backups_dir, _ = mock_backups

    # Create a simple config to backup
    (config_dir / "config.yml").write_text("test: config")

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.prefix = "test-"

    with patch("researcharr.cli.create_backup_file") as mock_create:
        mock_create.return_value = backups_dir / "test-backup.zip"

        result = cmd_create(args)

        assert result == 0
        mock_create.assert_called_once()


def test_cli_create_command_failure():
    """Test backup create command failure handling."""
    from researcharr.cli import cmd_create

    args = MagicMock()
    args.config_dir = "/nonexistent"
    args.prefix = ""

    with patch("researcharr.cli.create_backup_file") as mock_create:
        mock_create.return_value = None

        result = cmd_create(args)

        assert result == 1


def test_cli_list_command(mock_backups):
    """Test backup list command."""
    from researcharr.cli import cmd_list

    config_dir, backups_dir, backup_file = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.pattern = None
    args.json = False

    mock_backups_list = [
        {
            "name": backup_file.name,
            "size": backup_file.stat().st_size,
            "timestamp": "2025-01-10T12:00:00Z",
            "files": 5,
        }
    ]

    with patch("researcharr.cli.list_backups") as mock_list:
        mock_list.return_value = mock_backups_list

        result = cmd_list(args)

        assert result == 0
        mock_list.assert_called_once()


def test_cli_list_command_json(mock_backups, capsys):
    """Test backup list command with JSON output."""
    from researcharr.cli import cmd_list

    config_dir, _, backup_file = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.pattern = None
    args.json = True

    mock_backups_list = [
        {
            "name": backup_file.name,
            "size": 100,
            "timestamp": "2025-01-10T12:00:00Z",
        }
    ]

    with patch("researcharr.cli.list_backups") as mock_list:
        mock_list.return_value = mock_backups_list

        result = cmd_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "researcharr-backup" in captured.out


def test_cli_validate_command(mock_backups):
    """Test backup validate command."""
    from researcharr.cli import cmd_validate

    config_dir, _, backup_file = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.backup_name = backup_file.name

    with patch("researcharr.cli.validate_backup_file") as mock_validate:
        mock_validate.return_value = True

        result = cmd_validate(args)

        assert result == 0
        mock_validate.assert_called_once()


def test_cli_validate_command_invalid(mock_backups):
    """Test backup validate command with invalid backup."""
    from researcharr.cli import cmd_validate

    config_dir, _, backup_file = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.backup_name = backup_file.name

    with patch("researcharr.cli.validate_backup_file") as mock_validate:
        mock_validate.return_value = False

        result = cmd_validate(args)

        assert result == 1


def test_cli_info_command(mock_backups):
    """Test backup info command."""
    from researcharr.cli import cmd_info

    config_dir, _, backup_file = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.backup_name = backup_file.name
    args.json = False

    mock_info = {
        "metadata": {"timestamp": "2025-01-10T12:00:00Z", "app_version": "1.0.0"},
        "files": ["config.yml", "researcharr.db"],
    }

    with patch("researcharr.cli.get_backup_info") as mock_get_info:
        with patch("researcharr.cli.get_backup_size") as mock_size:
            mock_get_info.return_value = mock_info
            mock_size.return_value = 1024

            result = cmd_info(args)

            assert result == 0
            mock_get_info.assert_called_once()


def test_cli_prune_command(mock_backups):
    """Test backup prune command."""
    from researcharr.cli import cmd_prune

    config_dir, _, _ = mock_backups

    args = MagicMock()
    args.config_dir = str(config_dir)
    args.retain_count = 5
    args.retain_days = 30
    args.pre_restore_keep_days = 7

    with patch("researcharr.cli.list_backups") as mock_list:
        with patch("researcharr.cli.prune_backups") as mock_prune:
            mock_list.side_effect = [
                [{"name": "backup1"}, {"name": "backup2"}],  # before
                [{"name": "backup1"}],  # after
            ]

            result = cmd_prune(args)

            assert result == 0
            mock_prune.assert_called_once()


def test_format_size():
    """Test size formatting helper."""
    from researcharr.cli import format_size

    assert format_size(500) == "500.0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_format_timestamp():
    """Test timestamp formatting helper."""
    from researcharr.cli import format_timestamp

    result = format_timestamp("2025-01-10T12:00:00Z")
    assert "2025-01-10" in result
    assert "12:00:00" in result

    result = format_timestamp(None)
    assert result == "unknown"

    result = format_timestamp("invalid")
    assert result == "invalid"
