"""Tests for researcharr.backup_restore module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from researcharr.backup_restore import RestoreResult, restore_with_rollback


@pytest.fixture
def temp_config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def fake_backup_file(temp_config_dir):
    backup = temp_config_dir / "test_backup.zip"
    backup.write_text("fake backup")
    return backup


def test_restore_result_to_dict():
    result = RestoreResult(
        success=True,
        message="OK",
        backup_path="/path/to/backup.zip",
        snapshot_path="/path/to/snapshot.db",
        rollback_executed=False,
        errors=[],
    )
    d = result.to_dict()
    assert d["success"] is True
    assert d["message"] == "OK"
    assert "backup_path" in d


def test_restore_backup_not_found(temp_config_dir):
    result = restore_with_rollback(
        backup_path=temp_config_dir / "nonexistent.zip", config_dir=temp_config_dir
    )
    assert result.success is False
    assert "not found" in result.message.lower()
    assert len(result.errors) > 0


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_validation_failed(mock_monitor, mock_validate, fake_backup_file, temp_config_dir):
    mock_validate.return_value = False
    mock_monitor.return_value = MagicMock()

    result = restore_with_rollback(backup_path=fake_backup_file, config_dir=temp_config_dir)
    assert result.success is False
    assert "validation failed" in result.message.lower()


@patch("researcharr.backup_restore.read_backup_meta")
@patch("researcharr.backup_restore.get_alembic_head_revision")
@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_schema_mismatch_no_force(
    mock_monitor, mock_validate, mock_revision, mock_meta, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_meta.return_value = {"alembic_revision": "abc123"}
    mock_revision.return_value = "def456"
    mock_monitor.return_value = MagicMock()

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, force=False
    )
    assert result.success is False
    assert "mismatch" in result.message.lower()
    assert any("mismatch" in e.lower() for e in result.errors)


@patch("researcharr.backup_restore.read_backup_meta")
@patch("researcharr.backup_restore.get_alembic_head_revision")
@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.check_db_integrity")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_success_with_snapshot(
    mock_monitor,
    mock_integrity,
    mock_restore,
    mock_snapshot,
    mock_validate,
    mock_revision,
    mock_meta,
    fake_backup_file,
    temp_config_dir,
):
    mock_validate.return_value = True
    mock_meta.return_value = {"alembic_revision": "abc123"}
    mock_revision.return_value = "abc123"
    mock_snapshot.return_value = True
    mock_restore.return_value = True
    mock_integrity.return_value = True
    mock_monitor.return_value = MagicMock()

    # Create db file
    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(backup_path=fake_backup_file, config_dir=temp_config_dir)
    assert result.success is True
    assert result.snapshot_path is not None


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_fails_snapshot_creation(
    mock_monitor, mock_restore, mock_snapshot, mock_validate, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_snapshot.return_value = False
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(backup_path=fake_backup_file, config_dir=temp_config_dir)
    assert result.success is False
    assert "snapshot" in result.message.lower()


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_fails_with_rollback(
    mock_monitor, mock_restore, mock_snapshot, mock_validate, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_restore.return_value = False
    # snapshot creation succeeds, rollback succeeds
    mock_snapshot.return_value = True
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=True
    )
    assert result.success is False
    assert result.rollback_executed is True
    assert "rollback executed" in result.message.lower()


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_fails_no_rollback(
    mock_monitor, mock_restore, mock_snapshot, mock_validate, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_restore.return_value = False
    mock_snapshot.return_value = True
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=False
    )
    assert result.success is False
    assert result.rollback_executed is False


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_exception_with_rollback(
    mock_monitor, mock_restore, mock_snapshot, mock_validate, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_restore.side_effect = Exception("Restore error")
    mock_snapshot.return_value = True
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=True
    )
    assert result.success is False
    assert result.rollback_executed is True
    assert "exception" in result.message.lower()


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.check_db_integrity")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_integrity_check_fails_with_rollback(
    mock_monitor,
    mock_integrity,
    mock_restore,
    mock_snapshot,
    mock_validate,
    fake_backup_file,
    temp_config_dir,
):
    mock_validate.return_value = True
    mock_restore.return_value = True
    mock_snapshot.return_value = True
    mock_integrity.return_value = False
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=True
    )
    assert result.success is False
    assert result.rollback_executed is True
    assert "integrity" in result.message.lower()


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.check_db_integrity")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_success_cleanup_snapshot(
    mock_monitor,
    mock_integrity,
    mock_restore,
    mock_snapshot,
    mock_validate,
    fake_backup_file,
    temp_config_dir,
):
    mock_validate.return_value = True
    mock_restore.return_value = True
    mock_snapshot.return_value = True
    mock_integrity.return_value = True
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, cleanup_snapshot=True
    )
    assert result.success is True
    # Snapshot path should be None after cleanup
    assert result.snapshot_path is None


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_fails_rollback_also_fails(
    mock_monitor, mock_restore, mock_snapshot, mock_validate, fake_backup_file, temp_config_dir
):
    mock_validate.return_value = True
    mock_restore.return_value = False
    # First call (snapshot creation) succeeds, second call (rollback) fails
    mock_snapshot.side_effect = [True, False]
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=True
    )
    assert result.success is False
    assert "rollback" in result.message.lower() and "failed" in result.message.lower()


@patch("researcharr.backup_restore.validate_backup_file")
@patch("researcharr.backup_restore.snapshot_sqlite")
@patch("researcharr.backup_restore.restore_backup")
@patch("researcharr.backup_restore.check_db_integrity")
@patch("researcharr.backup_restore.get_backup_monitor")
def test_restore_integrity_fails_rollback_also_fails(
    mock_monitor,
    mock_integrity,
    mock_restore,
    mock_snapshot,
    mock_validate,
    fake_backup_file,
    temp_config_dir,
):
    mock_validate.return_value = True
    mock_restore.return_value = True
    mock_snapshot.side_effect = [True, False]  # create succeeds, rollback fails
    mock_integrity.return_value = False
    mock_monitor.return_value = MagicMock()

    db_path = temp_config_dir / "researcharr.db"
    db_path.write_text("fake db")

    result = restore_with_rollback(
        backup_path=fake_backup_file, config_dir=temp_config_dir, auto_rollback=True
    )
    assert result.success is False
    assert "rollback" in result.message.lower() and "failed" in result.message.lower()
