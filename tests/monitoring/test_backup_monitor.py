"""Tests for backup monitoring and alerting."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create mock configuration directory."""
    config_dir = tmp_path / "config"
    backups_dir = config_dir / "backups"
    backups_dir.mkdir(parents=True)
    return config_dir


def test_backup_health_monitor_init(mock_config_dir):
    """Test BackupHealthMonitor initialization."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    assert monitor.config_dir == mock_config_dir
    assert monitor.backups_dir == mock_config_dir / "backups"
    assert monitor.stale_threshold_hours == 48
    assert monitor.min_backup_count == 1


def test_check_backup_health_no_backups(mock_config_dir):
    """Test health check with no backups."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    with patch("researcharr.monitoring.backup_monitor.list_backups") as mock_list:
        mock_list.return_value = []

        health = monitor.check_backup_health()

        assert health["status"] == "error"
        assert health["backup_count"] == 0
        assert len(health["alerts"]) > 0
        assert any(alert["level"] == "error" for alert in health["alerts"])


def test_check_backup_health_with_backups(mock_config_dir):
    """Test health check with existing backups."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    mock_backups = [
        {
            "name": "researcharr-backup-20250110T120000Z.zip",
            "size": 1024 * 1024,
            "timestamp": "2025-01-10T12:00:00Z",
        }
    ]

    with patch("researcharr.monitoring.backup_monitor.list_backups") as mock_list:
        mock_list.return_value = mock_backups

        health = monitor.check_backup_health()

        assert health["backup_count"] == 1
        assert health["last_backup_name"] == mock_backups[0]["name"]
        assert health["last_backup_size_bytes"] == mock_backups[0]["size"]


def test_record_backup_created_success(mock_config_dir):
    """Test recording successful backup creation."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    backup_path = mock_config_dir / "backups" / "test-backup.zip"

    with patch("researcharr.monitoring.backup_monitor.get_backup_info") as mock_info:
        mock_info.return_value = {"size": 2048}

        monitor.record_backup_created(backup_path, success=True)

        metrics = monitor.get_metrics()
        assert metrics["successful_backup_count"] == 1
        assert metrics["failed_backup_count"] == 0
        assert metrics["last_backup_size_bytes"] == 2048


def test_record_backup_created_failure(mock_config_dir):
    """Test recording failed backup creation."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    backup_path = mock_config_dir / "backups" / "test-backup.zip"

    monitor.record_backup_created(backup_path, success=False)

    metrics = monitor.get_metrics()
    assert metrics["failed_backup_count"] == 1
    assert metrics["successful_backup_count"] == 0


def test_record_backup_restored_success(mock_config_dir):
    """Test recording successful backup restore."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    backup_path = mock_config_dir / "backups" / "test-backup.zip"

    monitor.record_backup_restored(backup_path, success=True)

    metrics = monitor.get_metrics()
    assert metrics["successful_restore_count"] == 1
    assert metrics["failed_restore_count"] == 0


def test_record_backup_restored_with_rollback(mock_config_dir):
    """Test recording restore with rollback."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    backup_path = mock_config_dir / "backups" / "test-backup.zip"

    monitor.record_backup_restored(backup_path, success=False, rollback=True)

    metrics = monitor.get_metrics()
    assert metrics["rollback_count"] == 1


def test_record_pre_restore_snapshot(mock_config_dir):
    """Test recording pre-restore snapshot creation."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    snapshot_path = mock_config_dir / "backups" / "pre-restore-snapshot.db"

    monitor.record_pre_restore_snapshot(snapshot_path)

    metrics = monitor.get_metrics()
    assert metrics["pre_restore_snapshots_count"] == 1


def test_record_backup_pruned(mock_config_dir):
    """Test recording backup pruning."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    # Just verify it doesn't raise an exception
    monitor.record_backup_pruned(removed_count=5)


def test_get_metrics(mock_config_dir):
    """Test getting metrics."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    monitor = BackupHealthMonitor(mock_config_dir)

    with patch("researcharr.monitoring.backup_monitor.list_backups") as mock_list:
        mock_list.return_value = [
            {"name": "backup1", "size": 1024},
            {"name": "backup2", "size": 2048},
        ]

        metrics = monitor.get_metrics()

        assert metrics["backup_count"] == 2
        assert metrics["total_size_bytes"] == 3072


def test_format_size():
    """Test size formatting."""
    from researcharr.monitoring.backup_monitor import BackupHealthMonitor

    assert BackupHealthMonitor._format_size(100) == "100.0 B"
    assert BackupHealthMonitor._format_size(1024) == "1.0 KB"
    assert BackupHealthMonitor._format_size(1024 * 1024) == "1.0 MB"


def test_get_backup_monitor_singleton():
    """Test global backup monitor singleton."""
    from researcharr.monitoring.backup_monitor import get_backup_monitor

    monitor1 = get_backup_monitor()
    monitor2 = get_backup_monitor()

    assert monitor1 is monitor2
