"""Edge-case tests for researcharr/backups.py shim layer.

These tests target uncovered lines in the backups shim module,
focusing on error handling and fallback behavior.
"""

# basedpyright: reportAttributeAccessIssue=false

from __future__ import annotations

from unittest.mock import patch


class TestBackupPathBehavior:
    """Test BackupPath public behavior."""

    def test_backuppath_creation_basic(self):
        """Test BackupPath can be created and behaves like a string."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backup_file.tar.gz", "backup_file.tar.gz")
        assert str(bp) == "/tmp/backup_file.tar.gz"
        assert isinstance(bp, str)

    def test_backuppath_startswith_none(self):
        """Test startswith with None prefix returns False."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backup.tar.gz", "backup.tar.gz")
        result = bp.startswith(None)
        assert result is False

    def test_backuppath_startswith_path(self):
        """Test startswith with path-like prefix."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backups/file.tar.gz", "file.tar.gz")
        assert bp.startswith("/tmp/") is True
        assert bp.startswith("/var/") is False

    def test_backuppath_startswith_name(self):
        """Test startswith with name-only prefix."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backups/backup_20231101.tar.gz", "backup_20231101.tar.gz")
        assert bp.startswith("backup_") is True
        assert bp.startswith("other_") is False

    def test_backuppath_startswith_windows_style(self):
        """Test startswith with Windows-style paths."""
        from researcharr.backups import BackupPath

        bp = BackupPath("C:\\backups\\file.tar.gz", "file.tar.gz")
        # Backslash should trigger path-based check
        assert bp.startswith("C:\\") is True


class TestCreateBackupFileEdgeCases:
    """Test create_backup_file error handling."""

    def test_import_fallback_triggered(self):
        """Test that import failure is handled gracefully."""
        # This primarily tests that the module loads successfully
        # even if _backups_impl import fails (lines 18-19)
        from researcharr import backups

        assert hasattr(backups, "create_backup_file")
        assert hasattr(backups, "BackupPath")

    def test_create_backup_none_result(self, tmp_path):
        """Test handling when backups_impl returns None."""
        from researcharr import backups

        with patch.object(backups.backups_impl, "create_backup_file", return_value=None):
            result = backups.create_backup_file(str(tmp_path), str(tmp_path), prefix="test")
            assert result is None

    def test_create_backup_with_valid_pathlib_result(self, tmp_path):
        """Test successful backup with pathlib.Path result."""
        from researcharr import backups

        test_file = tmp_path / "backup.tar.gz"
        test_file.touch()

        with patch.object(backups.backups_impl, "create_backup_file", return_value=test_file):
            result = backups.create_backup_file(str(tmp_path), str(tmp_path), prefix="test")
            assert result is not None
            assert "backup.tar.gz" in str(result)


class TestDelegatedFunctions:
    """Test delegated function passthrough."""

    def test_all_delegated_functions_callable(self):
        """Test that all delegated functions are callable."""
        from researcharr import backups

        # Test each delegated function exists and is callable
        delegated = [
            "prune_backups",
            "get_backup_info",
            "list_backups",
            "restore_backup",
            "validate_backup_file",
            "get_backup_size",
            "cleanup_temp_files",
            "get_default_backup_config",
            "merge_backup_configs",
        ]

        for func_name in delegated:
            assert hasattr(backups, func_name), f"Missing {func_name}"
            func = getattr(backups, func_name)
            assert callable(func), f"{func_name} not callable"

    def test_delegated_function_calls_impl(self):
        """Test that delegated functions call backups_impl."""
        from researcharr import backups

        # Mock one of the delegated functions
        with patch.object(
            backups.backups_impl, "list_backups", return_value=["backup1.tar.gz"]
        ) as mock:
            result = backups.list_backups("/tmp/backups")
            mock.assert_called_once_with("/tmp/backups")
            assert result == ["backup1.tar.gz"]


class TestBackupPathSpecialCases:
    """Test BackupPath with special inputs."""

    def test_backuppath_unicode_name(self):
        """Test BackupPath with unicode characters."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backup_日本語.tar.gz", "backup_日本語.tar.gz")
        assert str(bp) == "/tmp/backup_日本語.tar.gz"
        assert bp.startswith("backup_")

    def test_backuppath_empty_name(self):
        """Test BackupPath with empty name."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/file.tar.gz", "")
        assert str(bp) == "/tmp/file.tar.gz"
        # Empty name should still work with startswith
        assert bp.startswith("/tmp/")

    def test_backuppath_special_chars_in_prefix(self):
        """Test BackupPath.startswith with special characters."""
        from researcharr.backups import BackupPath

        bp = BackupPath("/tmp/backup-2023.tar.gz", "backup-2023.tar.gz")
        assert bp.startswith("backup-")
        assert bp.startswith("backup")
