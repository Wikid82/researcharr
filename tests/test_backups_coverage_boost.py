"""High-impact tests for backup system to boost coverage to 65%+.

This module targets all critical paths in researcharr.backups_impl with focus
on edge cases, error handling, and untested branches.
"""

import os
import time
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_backup_env(tmp_path):
    """Create a temporary environment for backup testing."""
    config_root = tmp_path / "config"
    backups_dir = tmp_path / "backups"
    config_root.mkdir()
    backups_dir.mkdir()

    # Create sample config files
    (config_root / "config.yml").write_text("app: researcharr\n")
    (config_root / "researcharr.db").write_bytes(b"fake_db_content")

    nested = config_root / "nested" / "deep"
    nested.mkdir(parents=True)
    (nested / "data.txt").write_text("nested data")

    return {
        "config_root": config_root,
        "backups_dir": backups_dir,
        "tmp_path": tmp_path,
    }


class TestBackupCreation:
    """Test create_backup_file with edge cases and error paths."""

    def test_create_backup_with_prefix(self, temp_backup_env):
        """Test backup creation with prefix."""
        from researcharr.backups_impl import create_backup_file

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
            prefix="test-",
        )

        assert result is not None
        assert Path(result).exists()
        assert "test-" in str(result)
        assert zipfile.is_zipfile(str(result))

    def test_create_backup_without_prefix(self, temp_backup_env):
        """Test backup creation without prefix."""
        from researcharr.backups_impl import create_backup_file

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert result is not None
        assert Path(result).exists()
        assert zipfile.is_zipfile(str(result))

    def test_create_backup_nonexistent_backups_dir(self, temp_backup_env):
        """Test backup creation creates backups_dir if missing."""
        from researcharr.backups_impl import create_backup_file

        new_backups_dir = temp_backup_env["tmp_path"] / "new_backups"
        result = create_backup_file(
            temp_backup_env["config_root"],
            new_backups_dir,
        )

        assert result is not None
        assert new_backups_dir.exists()
        assert Path(result).exists()

    def test_create_backup_includes_db_in_db_folder(self, temp_backup_env):
        """Test that researcharr.db is stored under db/ prefix in archive."""
        from researcharr.backups_impl import create_backup_file

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert result is not None
        with zipfile.ZipFile(str(result), "r") as zf:
            names = zf.namelist()
            # Check db/researcharr.db path
            assert any("db/researcharr.db" in n for n in names)

    def test_create_backup_includes_metadata(self, temp_backup_env):
        """Test backup includes metadata.txt."""
        from researcharr.backups_impl import create_backup_file

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert result is not None
        with zipfile.ZipFile(str(result), "r") as zf:
            assert "metadata.txt" in zf.namelist()
            metadata = zf.read("metadata.txt").decode("utf-8")
            assert "backup_created=" in metadata

    def test_create_backup_empty_config_root(self, temp_backup_env):
        """Test backup of empty config directory."""
        from researcharr.backups_impl import create_backup_file

        empty_config = temp_backup_env["tmp_path"] / "empty_config"
        empty_config.mkdir()

        result = create_backup_file(
            empty_config,
            temp_backup_env["backups_dir"],
        )

        assert result is not None
        assert zipfile.is_zipfile(str(result))
        with zipfile.ZipFile(str(result), "r") as zf:
            # Should still have metadata
            assert "metadata.txt" in zf.namelist()

    def test_create_backup_nonexistent_config_root(self, temp_backup_env):
        """Test backup handles nonexistent config_root gracefully."""
        from researcharr.backups_impl import create_backup_file

        nonexistent = temp_backup_env["tmp_path"] / "nonexistent"

        result = create_backup_file(
            nonexistent,
            temp_backup_env["backups_dir"],
            prefix="test-",
        )

        # Should still create backup with just metadata
        assert result is not None
        assert zipfile.is_zipfile(str(result))

    def test_create_backup_invalid_backups_dir_permissions(self, temp_backup_env, monkeypatch):
        """Test backup returns None if backups_dir can't be created."""
        from researcharr.backups_impl import create_backup_file

        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Cannot create directory")

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["tmp_path"] / "bad_perms",
        )

        assert result is None

    def test_create_backup_includes_nested_files(self, temp_backup_env):
        """Test backup includes deeply nested files."""
        from researcharr.backups_impl import create_backup_file

        result = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert result is not None
        with zipfile.ZipFile(str(result), "r") as zf:
            names = zf.namelist()
            # Check nested files are included
            assert any("data.txt" in n for n in names)


class TestBackupPruning:
    """Test prune_backups with various configurations."""

    def test_prune_by_retain_count(self, temp_backup_env):
        """Test pruning keeps only retain_count newest backups."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        # Create 5 backups
        for i in range(5):
            create_backup_file(
                temp_backup_env["config_root"],
                temp_backup_env["backups_dir"],
                prefix=f"backup{i}-",
            )
            time.sleep(0.01)  # Ensure different timestamps

        cfg = {"retain_count": 2}
        prune_backups(temp_backup_env["backups_dir"], cfg)

        remaining = list(temp_backup_env["backups_dir"].glob("*.zip"))
        assert len(remaining) == 2

    def test_prune_by_retain_days(self, temp_backup_env):
        """Test pruning by age (retain_days)."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        # Create backup
        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        # Make it old by modifying mtime
        old_time = time.time() - (31 * 86400)  # 31 days old
        os.utime(str(backup), (old_time, old_time))

        cfg = {"retain_days": 30}
        prune_backups(temp_backup_env["backups_dir"], cfg)

        remaining = list(temp_backup_env["backups_dir"].glob("*.zip"))
        assert len(remaining) == 0

    def test_prune_keeps_pre_restore_backups(self, temp_backup_env):
        """Test pre- prefixed backups respect pre_restore_keep_days."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        # Create regular backup (old)
        regular = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )
        old_time = time.time() - (31 * 86400)
        os.utime(str(regular), (old_time, old_time))

        # Create pre-restore backup (old)
        pre_backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
            prefix="pre-",
        )
        os.utime(str(pre_backup), (old_time, old_time))

        cfg = {"retain_days": 30, "pre_restore_keep_days": 90}
        prune_backups(temp_backup_env["backups_dir"], cfg)

        remaining = list(temp_backup_env["backups_dir"].glob("*.zip"))
        # pre- backup should remain, regular should be deleted
        assert len(remaining) == 1
        assert "pre-" in str(remaining[0])

    def test_prune_with_empty_config(self, temp_backup_env):
        """Test prune does nothing with empty config."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        before = list(temp_backup_env["backups_dir"].glob("*.zip"))
        prune_backups(temp_backup_env["backups_dir"], {})
        after = list(temp_backup_env["backups_dir"].glob("*.zip"))

        assert len(before) == len(after)

    def test_prune_with_none_config(self, temp_backup_env):
        """Test prune does nothing with None config."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        before = list(temp_backup_env["backups_dir"].glob("*.zip"))
        prune_backups(temp_backup_env["backups_dir"], None)
        after = list(temp_backup_env["backups_dir"].glob("*.zip"))

        assert len(before) == len(after)

    def test_prune_nonexistent_directory(self):
        """Test prune handles nonexistent directory gracefully."""
        from researcharr.backups_impl import prune_backups

        result = prune_backups("/nonexistent/path", {"retain_count": 5})
        assert result is None

    def test_prune_with_legacy_retention_count_key(self, temp_backup_env):
        """Test prune accepts legacy 'retention_count' key."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        # Create 3 backups
        for i in range(3):
            create_backup_file(
                temp_backup_env["config_root"],
                temp_backup_env["backups_dir"],
                prefix=f"b{i}-",
            )
            time.sleep(0.01)

        cfg = {"retention_count": 1}  # Legacy key
        prune_backups(temp_backup_env["backups_dir"], cfg)

        remaining = list(temp_backup_env["backups_dir"].glob("*.zip"))
        assert len(remaining) == 1

    def test_prune_ignores_non_zip_files(self, temp_backup_env):
        """Test prune only affects .zip files."""
        from researcharr.backups_impl import create_backup_file, prune_backups

        # Create multiple backups so retain_count=0 will try to delete them
        for i in range(3):
            create_backup_file(
                temp_backup_env["config_root"],
                temp_backup_env["backups_dir"],
            )
            time.sleep(0.01)

        # Create non-zip file
        (temp_backup_env["backups_dir"] / "readme.txt").write_text("test")

        cfg = {"retain_count": 0}
        prune_backups(temp_backup_env["backups_dir"], cfg)

        # txt file should still exist
        assert (temp_backup_env["backups_dir"] / "readme.txt").exists()
        # All zips should be deleted with retain_count=0
        assert len(list(temp_backup_env["backups_dir"].glob("*.zip"))) == 0


class TestBackupListing:
    """Test list_backups functionality."""

    def test_list_backups_includes_metadata(self, temp_backup_env):
        """Test list_backups returns name, path, size, mtime."""
        from researcharr.backups_impl import create_backup_file, list_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        backups = list_backups(temp_backup_env["backups_dir"])

        assert len(backups) == 1
        assert "name" in backups[0]
        assert "path" in backups[0]
        assert "size" in backups[0]
        assert "mtime" in backups[0]

    def test_list_backups_includes_files_list(self, temp_backup_env):
        """Test list_backups includes file list from zip."""
        from researcharr.backups_impl import create_backup_file, list_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        backups = list_backups(temp_backup_env["backups_dir"])

        assert "files" in backups[0]
        assert isinstance(backups[0]["files"], list)
        assert len(backups[0]["files"]) > 0

    def test_list_backups_sorted_by_name_reverse(self, temp_backup_env):
        """Test backups are sorted by name in reverse order."""
        from researcharr.backups_impl import create_backup_file, list_backups

        # Create multiple backups
        for i in range(3):
            create_backup_file(
                temp_backup_env["config_root"],
                temp_backup_env["backups_dir"],
                prefix=f"backup{i}-",
            )
            time.sleep(0.01)

        backups = list_backups(temp_backup_env["backups_dir"])

        assert len(backups) == 3
        # Should be reverse sorted by name
        names = [b["name"] for b in backups]
        assert names == sorted(names, reverse=True)

    def test_list_backups_empty_directory(self, temp_backup_env):
        """Test list_backups returns empty list for empty directory."""
        from researcharr.backups_impl import list_backups

        backups = list_backups(temp_backup_env["backups_dir"])
        assert backups == []

    def test_list_backups_nonexistent_directory(self):
        """Test list_backups returns empty list for nonexistent directory."""
        from researcharr.backups_impl import list_backups

        backups = list_backups("/nonexistent/path")
        assert backups == []

    def test_list_backups_with_pattern(self, temp_backup_env):
        """Test list_backups filters by pattern."""
        from researcharr.backups_impl import create_backup_file, list_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
            prefix="pre-",
        )
        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
            prefix="manual-",
        )

        backups = list_backups(temp_backup_env["backups_dir"], pattern="pre-")

        assert len(backups) == 1
        assert "pre-" in backups[0]["name"]

    def test_list_backups_ignores_non_zip_files(self, temp_backup_env):
        """Test list_backups only returns .zip files."""
        from researcharr.backups_impl import create_backup_file, list_backups

        create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        # Create non-zip file
        (temp_backup_env["backups_dir"] / "readme.txt").write_text("test")

        backups = list_backups(temp_backup_env["backups_dir"])

        assert len(backups) == 1
        assert backups[0]["name"].endswith(".zip")


class TestBackupRestore:
    """Test restore_backup functionality."""

    def test_restore_backup_success(self, temp_backup_env):
        """Test successful backup restoration."""
        from researcharr.backups_impl import create_backup_file, restore_backup

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        restore_dir = temp_backup_env["tmp_path"] / "restore"
        restore_dir.mkdir()

        result = restore_backup(backup, restore_dir)

        assert result is True
        # Check files were restored
        restored_files = list(restore_dir.rglob("*"))
        assert len(restored_files) > 0

    def test_restore_backup_nonexistent_file(self, temp_backup_env):
        """Test restore returns False for nonexistent backup."""
        from researcharr.backups_impl import restore_backup

        restore_dir = temp_backup_env["tmp_path"] / "restore"
        restore_dir.mkdir()

        result = restore_backup("/nonexistent/backup.zip", restore_dir)

        assert result is False

    def test_restore_backup_nonexistent_dest_raises(self, temp_backup_env):
        """Test restore raises Exception when dest doesn't exist."""
        from researcharr.backups_impl import create_backup_file, restore_backup

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        with pytest.raises(Exception, match="restore destination does not exist"):
            restore_backup(backup, "/nonexistent/restore")

    def test_restore_backup_invalid_zip_raises(self, temp_backup_env):
        """Test restore raises Exception for invalid zip file."""
        from researcharr.backups_impl import restore_backup

        # Create invalid zip file
        bad_zip = temp_backup_env["backups_dir"] / "bad.zip"
        bad_zip.write_text("not a zip file")

        restore_dir = temp_backup_env["tmp_path"] / "restore"
        restore_dir.mkdir()

        with pytest.raises(Exception, match="invalid backup file"):
            restore_backup(bad_zip, restore_dir)

    def test_restore_backup_extracts_files_correctly(self, temp_backup_env):
        """Test restored files match original content."""
        from researcharr.backups_impl import create_backup_file, restore_backup

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        restore_dir = temp_backup_env["tmp_path"] / "restore"
        restore_dir.mkdir()

        restore_backup(backup, restore_dir)

        # Check metadata file
        assert (restore_dir / "metadata.txt").exists()
        content = (restore_dir / "metadata.txt").read_text()
        assert "backup_created=" in content


class TestBackupValidation:
    """Test validate_backup_file functionality."""

    def test_validate_backup_valid_zip(self, temp_backup_env):
        """Test validation returns True for valid zip."""
        from researcharr.backups_impl import (
            create_backup_file,
            validate_backup_file,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert validate_backup_file(backup) is True

    def test_validate_backup_invalid_zip(self, temp_backup_env):
        """Test validation returns False for invalid zip."""
        from researcharr.backups_impl import validate_backup_file

        bad_zip = temp_backup_env["backups_dir"] / "bad.zip"
        bad_zip.write_text("not a zip")

        assert validate_backup_file(bad_zip) is False

    def test_validate_backup_nonexistent_file(self):
        """Test validation returns False for nonexistent file."""
        from researcharr.backups_impl import validate_backup_file

        assert validate_backup_file("/nonexistent/backup.zip") is False

    def test_validate_backup_with_string_path(self, temp_backup_env):
        """Test validation works with string paths."""
        from researcharr.backups_impl import (
            create_backup_file,
            validate_backup_file,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        assert validate_backup_file(str(backup)) is True


class TestBackupSize:
    """Test get_backup_size functionality."""

    def test_get_backup_size_returns_bytes(self, temp_backup_env):
        """Test get_backup_size returns file size in bytes."""
        from researcharr.backups_impl import (
            create_backup_file,
            get_backup_size,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        size = get_backup_size(backup)

        assert isinstance(size, int)
        assert size > 0

    def test_get_backup_size_nonexistent_file(self):
        """Test get_backup_size returns 0 for nonexistent file."""
        from researcharr.backups_impl import get_backup_size

        size = get_backup_size("/nonexistent/backup.zip")
        assert size == 0

    def test_get_backup_size_with_string_path(self, temp_backup_env):
        """Test get_backup_size works with string paths."""
        from researcharr.backups_impl import (
            create_backup_file,
            get_backup_size,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        size = get_backup_size(str(backup))
        assert size > 0


class TestBackupCleanup:
    """Test cleanup_temp_files functionality."""

    def test_cleanup_removes_files_in_directory(self, temp_backup_env):
        """Test cleanup removes all files in directory."""
        from researcharr.backups_impl import cleanup_temp_files

        cleanup_dir = temp_backup_env["tmp_path"] / "cleanup"
        cleanup_dir.mkdir()

        # Create test files
        (cleanup_dir / "file1.txt").write_text("test")
        (cleanup_dir / "file2.txt").write_text("test")

        cleanup_temp_files(cleanup_dir)

        # Files should be removed
        assert len(list(cleanup_dir.iterdir())) == 0

    def test_cleanup_removes_subdirectories(self, temp_backup_env):
        """Test cleanup removes subdirectories."""
        from researcharr.backups_impl import cleanup_temp_files

        cleanup_dir = temp_backup_env["tmp_path"] / "cleanup"
        cleanup_dir.mkdir()

        # Create subdirectory
        subdir = cleanup_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("test")

        cleanup_temp_files(cleanup_dir)

        # Subdirectory should be removed
        assert not subdir.exists()

    def test_cleanup_with_none_path(self):
        """Test cleanup handles None path gracefully."""
        from researcharr.backups_impl import cleanup_temp_files

        result = cleanup_temp_files(None)
        assert result is None

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup handles nonexistent directory gracefully."""
        from researcharr.backups_impl import cleanup_temp_files

        # Should not raise exception
        cleanup_temp_files("/nonexistent/path")

    def test_cleanup_with_permission_errors(self, temp_backup_env, monkeypatch):
        """Test cleanup continues on permission errors."""
        from researcharr.backups_impl import cleanup_temp_files

        cleanup_dir = temp_backup_env["tmp_path"] / "cleanup"
        cleanup_dir.mkdir()
        (cleanup_dir / "file.txt").write_text("test")

        # Mock unlink to raise exception
        def mock_unlink(self, *args, **kwargs):
            raise PermissionError("Cannot delete")

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        # Should not raise exception
        cleanup_temp_files(cleanup_dir)


class TestBackupConfig:
    """Test backup configuration functions."""

    def test_get_default_backup_config_returns_dict(self):
        """Test get_default_backup_config returns expected defaults."""
        from researcharr.backups_impl import get_default_backup_config

        config = get_default_backup_config()

        assert isinstance(config, dict)
        assert "retain_count" in config
        assert "retain_days" in config
        assert config["retain_count"] == 10
        assert config["retain_days"] == 30

    def test_merge_backup_configs_combines_dicts(self):
        """Test merge_backup_configs merges user config over defaults."""
        from researcharr.backups_impl import merge_backup_configs

        default = {"retain_count": 10, "retain_days": 30}
        user = {"retain_count": 5, "custom_key": "value"}

        merged = merge_backup_configs(default, user)

        assert merged["retain_count"] == 5  # User override
        assert merged["retain_days"] == 30  # Default preserved
        assert merged["custom_key"] == "value"  # User addition

    def test_merge_backup_configs_with_none_default(self):
        """Test merge handles None default config."""
        from researcharr.backups_impl import merge_backup_configs

        user = {"retain_count": 5}
        merged = merge_backup_configs(None, user)

        assert merged["retain_count"] == 5

    def test_merge_backup_configs_with_none_user(self):
        """Test merge handles None user config."""
        from researcharr.backups_impl import merge_backup_configs

        default = {"retain_count": 10}
        merged = merge_backup_configs(default, None)

        assert merged["retain_count"] == 10

    def test_merge_backup_configs_with_empty_dicts(self):
        """Test merge handles empty configs."""
        from researcharr.backups_impl import merge_backup_configs

        merged = merge_backup_configs({}, {})
        assert merged == {}


class TestBackupInfo:
    """Test get_backup_info functionality."""

    def test_get_backup_info_returns_metadata(self, temp_backup_env):
        """Test get_backup_info returns comprehensive metadata."""
        from researcharr.backups_impl import (
            create_backup_file,
            get_backup_info,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        info = get_backup_info(backup)

        assert info is not None
        assert "name" in info
        assert "path" in info
        assert "size" in info
        assert "mtime" in info

    def test_get_backup_info_includes_files_list(self, temp_backup_env):
        """Test get_backup_info includes file list for valid zips."""
        from researcharr.backups_impl import (
            create_backup_file,
            get_backup_info,
        )

        backup = create_backup_file(
            temp_backup_env["config_root"],
            temp_backup_env["backups_dir"],
        )

        info = get_backup_info(backup)

        assert "files" in info
        assert isinstance(info["files"], list)
        assert len(info["files"]) > 0

    def test_get_backup_info_nonexistent_file(self):
        """Test get_backup_info returns None for nonexistent file."""
        from researcharr.backups_impl import get_backup_info

        info = get_backup_info("/nonexistent/backup.zip")
        assert info is None

    def test_get_backup_info_invalid_zip(self, temp_backup_env):
        """Test get_backup_info handles invalid zip gracefully."""
        from researcharr.backups_impl import get_backup_info

        bad_zip = temp_backup_env["backups_dir"] / "bad.zip"
        bad_zip.write_text("not a zip")

        info = get_backup_info(bad_zip)

        # Should still return basic info, just no files list
        assert info is not None
        assert "name" in info
        assert "size" in info
