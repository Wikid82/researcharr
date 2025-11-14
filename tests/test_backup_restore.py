"""Comprehensive tests for backup_restore module with rollback capabilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from researcharr.backup_restore import RestoreResult, restore_with_rollback


class TestRestoreResult:
    """Test RestoreResult data class."""

    def test_create_success_result(self):
        """Test creating successful restore result."""
        result = RestoreResult(
            success=True,
            message="Restore completed",
            backup_path="/config/backups/test.tar.gz",
        )

        assert result.success is True
        assert result.message == "Restore completed"
        assert result.backup_path == Path("/config/backups/test.tar.gz")
        assert result.snapshot_path is None
        assert result.rollback_executed is False
        assert result.errors == []

    def test_create_failure_result_with_errors(self):
        """Test creating failure result with errors."""
        result = RestoreResult(
            success=False,
            message="Restore failed",
            backup_path="/config/backups/test.tar.gz",
            errors=["Error 1", "Error 2"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "Error 1" in result.errors

    def test_create_result_with_snapshot(self):
        """Test creating result with snapshot path."""
        result = RestoreResult(
            success=False,
            message="Rolled back",
            backup_path="/config/backups/test.tar.gz",
            snapshot_path="/config/backups/snapshot.db",
            rollback_executed=True,
        )

        assert result.snapshot_path == Path("/config/backups/snapshot.db")
        assert result.rollback_executed is True

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = RestoreResult(
            success=True,
            message="Done",
            backup_path="/config/backups/test.tar.gz",
            snapshot_path="/config/backups/snap.db",
            errors=["warning"],
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["message"] == "Done"
        assert data["backup_path"] == "/config/backups/test.tar.gz"
        assert data["snapshot_path"] == "/config/backups/snap.db"
        assert data["rollback_executed"] is False
        assert data["errors"] == ["warning"]

    def test_to_dict_no_snapshot(self):
        """Test to_dict with no snapshot."""
        result = RestoreResult(
            success=True,
            message="Success",
            backup_path="/test.tar.gz",
        )

        data = result.to_dict()
        assert data["snapshot_path"] is None


class TestRestoreWithRollbackValidation:
    """Test backup validation logic."""

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_backup_not_found(self, mock_monitor, mock_validate, tmp_path):
        """Test restore when backup file doesn't exist."""
        nonexistent = tmp_path / "missing.tar.gz"

        result = restore_with_rollback(nonexistent)

        assert result.success is False
        assert "not found" in result.message.lower()
        assert "does not exist" in result.errors[0].lower()

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_backup_validation_failed(self, mock_monitor, mock_validate, tmp_path):
        """Test restore when backup validation fails."""
        backup = tmp_path / "corrupt.tar.gz"
        backup.touch()

        mock_validate.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup)

        assert result.success is False
        assert "validation failed" in result.message.lower()
        monitor_instance.record_backup_restored.assert_called_once_with(
            backup, success=False
        )

    @patch("researcharr.backup_restore.read_backup_meta")
    @patch("researcharr.backup_restore.get_alembic_head_revision")
    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_schema_version_mismatch_without_force(
        self, mock_monitor, mock_validate, mock_get_rev, mock_read_meta, tmp_path
    ):
        """Test restore fails on schema version mismatch without force."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        mock_validate.return_value = True
        mock_get_rev.return_value = "abc123"
        mock_read_meta.return_value = {"alembic_revision": "def456"}

        result = restore_with_rollback(backup, force=False)

        assert result.success is False
        assert "schema version mismatch" in result.message.lower()
        assert len(result.errors) >= 1

    @patch("researcharr.backup_restore.read_backup_meta")
    @patch("researcharr.backup_restore.get_alembic_head_revision")
    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_schema_version_mismatch_with_force(
        self,
        mock_monitor,
        mock_integrity,
        mock_restore,
        mock_snapshot,
        mock_validate,
        mock_get_rev,
        mock_read_meta,
        tmp_path,
    ):
        """Test restore proceeds on schema mismatch when force=True."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_get_rev.return_value = "abc123"
        mock_read_meta.return_value = {"alembic_revision": "def456"}
        mock_snapshot.return_value = True
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, force=True)

        assert result.success is True
        mock_restore.assert_called_once()


class TestRestoreWithRollbackSnapshots:
    """Test snapshot creation and management."""

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_snapshot_creation_failure(
        self, mock_monitor, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test restore fails if snapshot creation fails."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir)

        assert result.success is False
        assert "snapshot" in result.message.lower()
        monitor_instance.record_backup_restored.assert_called_once_with(
            backup, success=False
        )

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_snapshot_created_before_restore(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test that snapshot is created before restore."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = True
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir)

        assert result.success is True
        # Snapshot should be created
        assert mock_snapshot.call_count >= 1
        monitor_instance.record_pre_restore_snapshot.assert_called_once()


class TestRestoreWithRollbackRestoreProcess:
    """Test actual restore process."""

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_successful_restore(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test fully successful restore."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = True
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir)

        assert result.success is True
        assert "successfully" in result.message.lower()
        mock_restore.assert_called_once_with(backup, config_dir)
        monitor_instance.record_backup_restored.assert_called_once_with(
            backup, success=True
        )

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_restore_failure_with_rollback(
        self, mock_monitor, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test rollback executed when restore fails."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        # First call for snapshot, second for rollback
        mock_snapshot.side_effect = [True, True]
        mock_restore.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, auto_rollback=True)

        assert result.success is False
        assert result.rollback_executed is True
        assert "rollback executed" in result.message.lower()
        monitor_instance.record_backup_restored.assert_called_once_with(
            backup, success=False, rollback=True
        )

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_restore_failure_without_rollback(
        self, mock_monitor, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test failure recorded when auto_rollback disabled."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = True
        mock_restore.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, auto_rollback=False)

        assert result.success is False
        assert result.rollback_executed is False

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_restore_exception_with_rollback(
        self, mock_monitor, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test rollback on restore exception."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.side_effect = [True, True]  # Snapshot then rollback
        mock_restore.side_effect = Exception("Restore failed!")
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, auto_rollback=True)

        assert result.success is False
        assert result.rollback_executed is True
        assert "exception" in result.message.lower()


class TestRestoreWithRollbackIntegrityCheck:
    """Test database integrity checking."""

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_integrity_check_failure_with_rollback(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test rollback when integrity check fails."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.side_effect = [True, True]  # Snapshot then rollback
        mock_restore.return_value = True
        mock_integrity.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, auto_rollback=True)

        assert result.success is False
        assert result.rollback_executed is True
        assert "integrity" in result.message.lower()

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_integrity_check_pass(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test successful restore with passing integrity check."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = True
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir)

        assert result.success is True
        mock_integrity.assert_called_once()


class TestRestoreWithRollbackCleanup:
    """Test snapshot cleanup logic."""

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_snapshot_not_cleaned_by_default(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test that snapshot is preserved by default."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        mock_snapshot.return_value = True
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, cleanup_snapshot=False)

        assert result.success is True
        assert result.snapshot_path is not None

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.check_db_integrity")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_snapshot_cleaned_when_requested(
        self, mock_monitor, mock_integrity, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test that snapshot is removed when cleanup_snapshot=True."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        backups_dir = config_dir / "backups"
        backups_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        # Create a real snapshot file to be deleted
        snapshot_file = backups_dir / "pre-restore-test.db"

        def create_snapshot(src, dst):
            snapshot_file.touch()
            return True

        mock_validate.return_value = True
        mock_snapshot.side_effect = create_snapshot
        mock_restore.return_value = True
        mock_integrity.return_value = True
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, cleanup_snapshot=True)

        assert result.success is True
        assert result.snapshot_path is None


class TestRestoreWithRollbackEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_dir_defaults_to_env(self, tmp_path, monkeypatch):
        """Test that config_dir defaults to CONFIG_DIR env var."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        monkeypatch.setenv("CONFIG_DIR", str(tmp_path / "custom"))

        with patch("researcharr.backup_restore.validate_backup_file") as mock_validate:
            mock_validate.return_value = False

            result = restore_with_rollback(backup)

            assert result.success is False

    @patch("researcharr.backup_restore.validate_backup_file")
    @patch("researcharr.backup_restore.snapshot_sqlite")
    @patch("researcharr.backup_restore.restore_backup")
    @patch("researcharr.backup_restore.get_backup_monitor")
    def test_rollback_failure(
        self, mock_monitor, mock_restore, mock_snapshot, mock_validate, tmp_path
    ):
        """Test when both restore and rollback fail."""
        backup = tmp_path / "backup.tar.gz"
        backup.touch()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_path = config_dir / "researcharr.db"
        db_path.touch()

        mock_validate.return_value = True
        # First call for snapshot succeeds, second (rollback) fails
        mock_snapshot.side_effect = [True, False]
        mock_restore.return_value = False
        monitor_instance = MagicMock()
        mock_monitor.return_value = monitor_instance

        result = restore_with_rollback(backup, config_dir=config_dir, auto_rollback=True)

        assert result.success is False
        assert "rollback" in result.message.lower()
        assert "failed" in result.message.lower()
        assert any("manual recovery" in err.lower() for err in result.errors)
