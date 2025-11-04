"""Tests for backups.py module to improve coverage."""

import os
import tempfile
import zipfile
import pytest

import backups


class TestBackupsModule:
    """Test the backups.py module functions."""

    def test_create_backup_file_basic(self):
        """Test basic backup file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_root = temp_dir
            backups_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backups_dir)

            # Create some test files to backup
            test_file = os.path.join(config_root, "test_config.yml")
            with open(test_file, "w") as f:
                f.write("test: config\n")

            backup_name = backups.create_backup_file(config_root, backups_dir)

            assert backup_name is not None
            assert backup_name.endswith(".zip")

            backup_path = os.path.join(backups_dir, backup_name)
            assert os.path.exists(backup_path)

    def test_create_backup_file_with_prefix(self):
        """Test backup file creation with prefix."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_root = temp_dir
            backups_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backups_dir)

            backup_name = backups.create_backup_file(config_root, backups_dir, "test_prefix")

            assert backup_name is not None
            assert backup_name.startswith("test_prefix")

    def test_create_backup_file_empty_directory(self):
        """Test backup creation with empty config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_root = temp_dir
            backups_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backups_dir)

            backup_name = backups.create_backup_file(config_root, backups_dir)

            assert backup_name is not None
            backup_path = os.path.join(backups_dir, backup_name)
            assert os.path.exists(backup_path)

    def test_create_backup_file_invalid_paths(self):
        """Test backup creation with invalid paths."""
        # Invalid config root - should still create empty backup
        result = backups.create_backup_file("/nonexistent", "/tmp", "test")
        assert result is not None
        assert result.startswith("test")

        # Invalid backups directory
        with tempfile.TemporaryDirectory() as temp_dir:
            result = backups.create_backup_file(temp_dir, "/invalid/backups/dir", "test")
            assert result is None

    def test_create_backup_file_with_subdirectories(self):
        """Test backup creation with subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_root = temp_dir
            backups_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backups_dir)

            # Create subdirectory with files
            sub_dir = os.path.join(config_root, "plugins")
            os.makedirs(sub_dir)

            sub_file = os.path.join(sub_dir, "plugin_config.yml")
            with open(sub_file, "w") as f:
                f.write("plugin: config\n")

            backup_name = backups.create_backup_file(config_root, backups_dir)
            assert backup_name is not None
            backup_path = os.path.join(backups_dir, backup_name)

            # Verify backup contains subdirectory
            with zipfile.ZipFile(backup_path, "r") as zip_file:
                names = zip_file.namelist()
                assert any("plugins/" in name for name in names)

    def test_prune_backups_by_count(self):
        """Test pruning backups by count."""
        with tempfile.TemporaryDirectory() as backups_dir:
            # Create test backup files
            for i in range(5):
                backup_name = f"backup_{i}_20241101_{str(120000 + i).zfill(6)}.zip"
                backup_path = os.path.join(backups_dir, backup_name)
                with open(backup_path, "w") as f:
                    f.write("test backup content")

            config = {"retain_count": 3}
            backups.prune_backups(backups_dir, config)

            # Should have only 3 files left
            remaining_files = [f for f in os.listdir(backups_dir) if f.endswith(".zip")]
            assert len(remaining_files) == 3

    def test_prune_backups_by_age(self):
        """Test pruning backups by age."""
        with tempfile.TemporaryDirectory() as backups_dir:
            # Create test backup files with different timestamps
            import time

            current_time = time.time()

            # Old backup (should be pruned)
            old_backup = os.path.join(backups_dir, "old_backup.zip")
            with open(old_backup, "w") as f:
                f.write("old backup")

            # Set old timestamp (older than 7 days)
            old_time = current_time - (8 * 24 * 60 * 60)
            os.utime(old_backup, (old_time, old_time))

            # Recent backup (should be kept)
            recent_backup = os.path.join(backups_dir, "recent_backup.zip")
            with open(recent_backup, "w") as f:
                f.write("recent backup")

            config = {"retain_days": 7}
            backups.prune_backups(backups_dir, config)

            # Only recent backup should remain
            remaining_files = os.listdir(backups_dir)
            assert "recent_backup.zip" in remaining_files
            assert "old_backup.zip" not in remaining_files

    def test_prune_backups_no_config(self):
        """Test pruning backups without configuration."""
        with tempfile.TemporaryDirectory() as backups_dir:
            # Create test backup file
            backup_path = os.path.join(backups_dir, "test_backup.zip")
            with open(backup_path, "w") as f:
                f.write("test")

            # Should not prune anything without config
            backups.prune_backups(backups_dir, None)
            assert os.path.exists(backup_path)

            backups.prune_backups(backups_dir, {})
            assert os.path.exists(backup_path)

    def test_prune_backups_invalid_directory(self):
        """Test pruning backups with invalid directory."""
        config = {"retain_count": 5}
        # Should not raise exception
        backups.prune_backups("/nonexistent/directory", config)

    def test_prune_backups_mixed_files(self):
        """Test pruning backups with mixed file types."""
        with tempfile.TemporaryDirectory() as backups_dir:
            # Create backup files and other files
            for i in range(3):
                backup_path = os.path.join(backups_dir, f"backup_{i}.zip")
                with open(backup_path, "w") as f:
                    f.write(f"backup {i}")

            # Create non-backup file
            other_file = os.path.join(backups_dir, "other_file.txt")
            with open(other_file, "w") as f:
                f.write("other content")

            config = {"retain_count": 2}
            backups.prune_backups(backups_dir, config)

            # Should have 2 backup files and 1 other file
            all_files = os.listdir(backups_dir)
            backup_files = [f for f in all_files if f.endswith(".zip")]

            assert len(backup_files) == 2
            assert "other_file.txt" in all_files

    @pytest.mark.skip(reason="get_backup_info function not implemented")
    def test_get_backup_info(self):
        """Test getting backup file information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, "test_backup.zip")

            # Create a test backup with some content
            with zipfile.ZipFile(backup_path, "w") as zip_file:
                zip_file.writestr("config.yml", "test: config")
                zip_file.writestr("plugins/plugin.yml", "plugin: test")

            info = backups.get_backup_info(backup_path)

            assert info is not None
            assert info["name"] == "test_backup.zip"
            assert info["size"] > 0
            assert info["files"] >= 2
            assert "created" in info

    @pytest.mark.skip(reason="get_backup_info function not implemented")
    def test_get_backup_info_invalid_file(self):
        """Test getting backup info for invalid file."""
        info = backups.get_backup_info("/nonexistent/backup.zip")
        assert info is None

    @pytest.mark.skip(reason="get_backup_info function not implemented")
    def test_get_backup_info_invalid_zip(self):
        """Test getting backup info for invalid zip file."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmpfile:
            tmpfile.write(b"not a zip file")
            invalid_zip = tmpfile.name

        try:
            info = backups.get_backup_info(invalid_zip)
            assert info is None
        finally:
            if os.path.exists(invalid_zip):
                os.unlink(invalid_zip)

    @pytest.mark.skip(reason="list_backups function not implemented")
    def test_list_backups(self):
        """Test listing backup files."""
        with tempfile.TemporaryDirectory() as backups_dir:
            # Create test backup files
            backup_names = ["backup_1.zip", "backup_2.zip", "backup_3.zip"]
            for name in backup_names:
                backup_path = os.path.join(backups_dir, name)
                with zipfile.ZipFile(backup_path, "w") as zip_file:
                    zip_file.writestr("test.txt", "test content")

            # Create non-backup file
            other_file = os.path.join(backups_dir, "other.txt")
            with open(other_file, "w") as f:
                f.write("other")

            backup_list = backups.list_backups(backups_dir)

            assert len(backup_list) == 3
            backup_file_names = [b["name"] for b in backup_list]
            for name in backup_names:
                assert name in backup_file_names

    @pytest.mark.skip(reason="list_backups function not implemented")
    def test_list_backups_empty_directory(self):
        """Test listing backups in empty directory."""
        with tempfile.TemporaryDirectory() as backups_dir:
            backup_list = backups.list_backups(backups_dir)
            assert backup_list == []

    @pytest.mark.skip(reason="list_backups function not implemented")
    def test_list_backups_invalid_directory(self):
        """Test listing backups in invalid directory."""
        backup_list = backups.list_backups("/nonexistent/directory")
        assert backup_list == []

    @pytest.mark.skip(reason="restore_backup function not implemented")
    def test_restore_backup(self):
        """Test restoring a backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source config directory
            config_root = os.path.join(temp_dir, "config")
            os.makedirs(config_root)

            # Create test file
            test_file = os.path.join(config_root, "test_config.yml")
            with open(test_file, "w") as f:
                f.write("original: config\n")

            # Create backup
            backups_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backups_dir)
            backup_name = backups.create_backup_file(config_root, backups_dir)
            assert backup_name is not None

            # Modify original file
            with open(test_file, "w") as f:
                f.write("modified: config\n")

            # Restore backup
            backup_path = os.path.join(backups_dir, backup_name)
            restore_dir = os.path.join(temp_dir, "restored")

            success = backups.restore_backup(backup_path, restore_dir)
            assert success is True

            # Verify restored content
            restored_file = os.path.join(restore_dir, "test_config.yml")
            assert os.path.exists(restored_file)

            with open(restored_file, "r") as f:
                content = f.read()
                assert "original: config" in content

    @pytest.mark.skip(reason="restore_backup function not implemented")
    def test_restore_backup_invalid_file(self):
        """Test restoring invalid backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            success = backups.restore_backup("/nonexistent/backup.zip", temp_dir)
            assert success is False

    @pytest.mark.skip(reason="restore_backup function not implemented")
    def test_restore_backup_invalid_destination(self):
        """Test restoring to invalid destination."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, "test.zip")
            with zipfile.ZipFile(backup_path, "w") as zip_file:
                zip_file.writestr("test.txt", "content")

            success = backups.restore_backup(backup_path, "/invalid/destination")
            assert success is False

    @pytest.mark.skip(reason="validate_backup_file function not implemented")
    def test_validate_backup_file(self):
        """Test validating backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid backup
            backup_path = os.path.join(temp_dir, "valid_backup.zip")
            with zipfile.ZipFile(backup_path, "w") as zip_file:
                zip_file.writestr("config.yml", "test: config")

            is_valid = backups.validate_backup_file(backup_path)
            assert is_valid is True

    @pytest.mark.skip(reason="validate_backup_file function not implemented")
    def test_validate_backup_file_invalid(self):
        """Test validating invalid backup file."""
        # Non-existent file
        is_valid = backups.validate_backup_file("/nonexistent/backup.zip")
        assert is_valid is False

        # Invalid zip file
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmpfile:
            tmpfile.write(b"not a zip file")
            invalid_zip = tmpfile.name

        try:
            is_valid = backups.validate_backup_file(invalid_zip)
            assert is_valid is False
        finally:
            if os.path.exists(invalid_zip):
                os.unlink(invalid_zip)

    @pytest.mark.skip(reason="get_backup_size function not implemented")
    def test_get_backup_size(self):
        """Test getting backup file size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, "test_backup.zip")

            with zipfile.ZipFile(backup_path, "w") as zip_file:
                zip_file.writestr("test.txt", "test content")

            size = backups.get_backup_size(backup_path)
            assert size > 0

    @pytest.mark.skip(reason="get_backup_size function not implemented")
    def test_get_backup_size_invalid_file(self):
        """Test getting size of invalid backup file."""
        size = backups.get_backup_size("/nonexistent/backup.zip")
        assert size == 0

    @pytest.mark.skip(reason="cleanup_temp_files function not implemented")
    def test_cleanup_temp_files(self):
        """Test cleaning up temporary files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some temp files
            temp_file1 = os.path.join(temp_dir, "temp_file_1.tmp")
            temp_file2 = os.path.join(temp_dir, "temp_file_2.tmp")

            with open(temp_file1, "w") as f:
                f.write("temp content 1")
            with open(temp_file2, "w") as f:
                f.write("temp content 2")

            # Clean up
            backups.cleanup_temp_files(temp_dir)

            # Temp files should be gone
            assert not os.path.exists(temp_file1)
            assert not os.path.exists(temp_file2)

    @pytest.mark.skip(reason="get_default_backup_config function not implemented")
    def test_get_default_backup_config(self):
        """Test getting default backup configuration."""
        config = backups.get_default_backup_config()

        assert isinstance(config, dict)
        assert "retain_count" in config
        assert "retain_days" in config
        assert config["retain_count"] > 0
        assert config["retain_days"] > 0

    @pytest.mark.skip(reason="merge_backup_configs function not implemented")
    def test_merge_backup_configs(self):
        """Test merging backup configurations."""
        default_config = {"retain_count": 10, "retain_days": 30, "enabled": True}
        user_config = {"retain_count": 5, "compress": True}

        merged = backups.merge_backup_configs(default_config, user_config)

        assert merged["retain_count"] == 5  # User override
        assert merged["retain_days"] == 30  # Default value
        assert merged["enabled"] is True  # Default value
        assert merged["compress"] is True  # User addition
