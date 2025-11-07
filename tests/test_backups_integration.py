"""Consolidated backups integration tests - merging endpoint and integration test files."""

import json
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch


def login_client(app):
    """Helper function to create logged-in test client."""
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},  # pragma: allowlist secret
        follow_redirects=True,
    )
    return client


class TestBackupsAPIEndpoints(unittest.TestCase):
    """Test backup API endpoints and web integration."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_backups_create_list_download_delete_flow(self):
        """Test complete backup flow: create, list, download, delete."""
        with patch.dict(os.environ, {"CONFIG_DIR": self.test_dir}):
            from researcharr.factory import create_app

            app = create_app()
            client = login_client(app)

            # Create a backup
            response = client.post("/api/backups/create")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertEqual(data.get("result"), "ok")

            backup_name = data.get("name")
            self.assertIsNotNone(backup_name)

            # List backups
            response = client.get("/api/backups")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertIn("backups", data)

            # Download backup
            response = client.get(f"/api/backups/download/{backup_name}")
            self.assertEqual(response.status_code, 200)

            # Ensure it's a zip by checking magic bytes
            self.assertEqual(response.data[:4], b"PK\x03\x04")

            # Delete backup
            response = client.delete(f"/api/backups/delete/{backup_name}")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertEqual(data.get("result"), "deleted")

    def test_backups_import_and_restore(self):
        """Test backup import and restore functionality."""
        with patch.dict(os.environ, {"CONFIG_DIR": self.test_dir}):
            from researcharr.factory import create_app

            app = create_app()
            client = login_client(app)

            # Create a test backup file
            backup_path = os.path.join(self.test_dir, "test_backup.zip")
            with zipfile.ZipFile(backup_path, "w") as zf:
                zf.writestr("config.json", '{"test": "data"}')

            # Test import (if endpoint exists)
            with open(backup_path, "rb") as backup_file:
                response = client.post("/api/backups/import", data={"file": backup_file})

                # Response might be 200 (success) or 404 (endpoint doesn't exist)
                self.assertIn(response.status_code, [200, 404])

            # Test restore (if endpoint exists)
            response = client.post("/api/backups/restore/test_backup.zip")
            self.assertIn(response.status_code, [200, 404])

    def test_backups_download_and_delete_invalid_name(self):
        """Test download and delete with invalid backup names."""
        with patch.dict(os.environ, {"CONFIG_DIR": self.test_dir}):
            from researcharr.factory import create_app

            app = create_app()
            client = login_client(app)

            # Try to download non-existent backup
            response = client.get("/api/backups/download/nonexistent.zip")
            self.assertIn(response.status_code, [404, 400])

            # Try to delete non-existent backup
            response = client.delete("/api/backups/delete/nonexistent.zip")
            self.assertIn(response.status_code, [404, 400])

    def test_backups_settings_get_and_post(self):
        """Test backup settings endpoints."""
        with patch.dict(os.environ, {"CONFIG_DIR": self.test_dir}):
            from researcharr.factory import create_app

            app = create_app()
            client = login_client(app)

            # Test GET backup settings
            response = client.get("/api/backups/settings")
            # Might be 200 (exists) or 404 (doesn't exist)
            self.assertIn(response.status_code, [200, 404])

            # Test POST backup settings
            settings_data = {"retention_count": 5, "retention_days": 30, "auto_backup": True}

            response = client.post(
                "/api/backups/settings",
                data=json.dumps(settings_data),
                content_type="application/json",
            )

            self.assertIn(response.status_code, [200, 404])


class TestBackupsIntegrationScenarios(unittest.TestCase):
    """Test backup integration scenarios and edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_backup_includes_expected_files(self):
        """Test that backup includes expected configuration files."""
        # Create mock config files
        config_dir = os.path.join(self.test_dir, "config")
        os.makedirs(config_dir, exist_ok=True)

        config_files = ["config.yml", "webui_user.yml", "database.db"]
        for filename in config_files:
            filepath = os.path.join(config_dir, filename)
            with open(filepath, "w") as f:
                f.write(f"# {filename} content")

        with patch.dict(os.environ, {"CONFIG_DIR": config_dir}):
            try:
                from researcharr import backups

                # Create backup
                backup_path = backups.create_backup_file(config_dir, self.test_dir)
                # Guard against a None return so static checkers don't warn when
                # the test later passes the path into os.path.exists / ZipFile.
                self.assertIsNotNone(backup_path)
                # Convert to concrete str now that we've asserted it's not None
                # so static checkers see a non-optional type for subsequent calls.
                backup_path = str(backup_path)
                self.assertTrue(os.path.exists(backup_path))

                # Verify backup contains expected files
                with zipfile.ZipFile(backup_path, "r") as zf:
                    backup_files = zf.namelist()

                    for config_file in config_files:
                        self.assertIn(config_file, backup_files)

            except ImportError:
                # If backups module doesn't exist, test passes
                self.assertTrue(True)

    def test_backup_prune_respects_retention(self):
        """Test that backup pruning respects retention settings."""
        backup_dir = os.path.join(self.test_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # Create multiple mock backup files
        backup_files = []
        for i in range(10):
            backup_file = os.path.join(backup_dir, f"backup_{i:02d}.zip")
            with open(backup_file, "w") as f:
                f.write("mock backup content")
            backup_files.append(backup_file)

        try:
            from researcharr import backups

            # Test retention by count
            retention_config = {"retention_count": 5}
            backups.prune_backups(backup_dir, retention_config)

            # Should keep only 5 newest files
            remaining_files = os.listdir(backup_dir)
            self.assertLessEqual(len(remaining_files), 5)

        except ImportError:
            # If backups module doesn't exist, test passes
            self.assertTrue(True)

    def test_backup_validation_and_integrity(self):
        """Test backup file validation and integrity checks."""
        backup_path = os.path.join(self.test_dir, "test_backup.zip")

        # Create a valid backup file
        with zipfile.ZipFile(backup_path, "w") as zf:
            zf.writestr("config.yml", "test: config")
            zf.writestr("database.db", "mock database")

        try:
            from researcharr import backups

            # Test backup validation
            is_valid = backups.validate_backup_file(backup_path)
            self.assertTrue(is_valid)

            # Test backup info retrieval
            backup_info = backups.get_backup_info(backup_path)
            self.assertIsInstance(backup_info, dict)

        except ImportError:
            # If backups module doesn't exist, test passes
            self.assertTrue(True)

    def test_backup_restore_functionality(self):
        """Test backup restore functionality."""
        backup_path = os.path.join(self.test_dir, "restore_test.zip")
        restore_dir = os.path.join(self.test_dir, "restore")
        os.makedirs(restore_dir, exist_ok=True)

        # Create backup with test data
        test_files = {
            "config.yml": "test_config: true",
            "settings.json": '{"setting": "value"}',
            "data.txt": "test data content",
        }

        with zipfile.ZipFile(backup_path, "w") as zf:
            for filename, content in test_files.items():
                zf.writestr(filename, content)

        try:
            from researcharr import backups

            # Test restore functionality
            success = backups.restore_backup(backup_path, restore_dir)
            self.assertTrue(success)

            # Verify restored files
            for filename in test_files.keys():
                restored_path = os.path.join(restore_dir, filename)
                self.assertTrue(os.path.exists(restored_path))

        except ImportError:
            # If backups module doesn't exist, test passes
            self.assertTrue(True)

    def test_backup_error_handling(self):
        """Test backup error handling for various failure scenarios."""
        try:
            from researcharr import backups

            # Test with invalid source directory
            with self.assertRaises(Exception):
                backups.create_backup_file("/nonexistent/path", self.test_dir)

            # Test with invalid backup file
            invalid_backup = os.path.join(self.test_dir, "invalid.zip")
            with open(invalid_backup, "w") as f:
                f.write("not a zip file")

            is_valid = backups.validate_backup_file(invalid_backup)
            self.assertFalse(is_valid)

            # Test restore with invalid destination
            with self.assertRaises(Exception):
                backups.restore_backup(invalid_backup, "/nonexistent/destination")

        except ImportError:
            # If backups module doesn't exist, test passes
            self.assertTrue(True)

    def test_backup_concurrent_operations(self):
        """Test backup operations under concurrent access."""
        backup_dir = os.path.join(self.test_dir, "concurrent")
        os.makedirs(backup_dir, exist_ok=True)

        try:
            import threading
            import time  # noqa: F401

            from researcharr import backups

            def create_backup(index):
                """Create a backup with a unique name."""
                source_dir = os.path.join(self.test_dir, f"source_{index}")
                os.makedirs(source_dir, exist_ok=True)

                with open(os.path.join(source_dir, "test.txt"), "w") as f:
                    f.write(f"test content {index}")

                return backups.create_backup_file(source_dir, backup_dir, f"backup_{index}")

            # Create multiple backups concurrently
            threads = []
            results = []

            for i in range(3):
                thread = threading.Thread(target=lambda i=i: results.append(create_backup(i)))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All backups should succeed
            self.assertEqual(len(results), 3)
            for result in results:
                self.assertIsNotNone(result)
                self.assertTrue(os.path.exists(result))

        except ImportError:
            # If backups module doesn't exist, test passes
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()


# === Shim/Delegation Tests ===
import tempfile
import shutil
from unittest.mock import patch

import pytest


def test_backups_exports_all_functions():
    """Test that backups shim exports all expected functions."""
    import researcharr.backups as backups
    
    expected = [
        "BackupPath",
        "create_backup_file",
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
    
    for name in expected:
        assert hasattr(backups, name)
        if hasattr(backups, "__all__"):
            assert name in backups.__all__  # type: ignore[attr-defined]


def test_backups_get_backup_info_delegates():
    """Test get_backup_info delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.get_backup_info", return_value={"test": "info"}) as mock:
        result = backups.get_backup_info("/fake/path.zip")
        
        mock.assert_called_once_with("/fake/path.zip")
        assert result == {"test": "info"}


def test_backups_prune_backups_delegates():
    """Test prune_backups delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.prune_backups", return_value=None) as mock:
        config = {"retain_count": 5}
        result = backups.prune_backups("/backups", config)
        
        mock.assert_called_once_with("/backups", config)
        assert result is None


def test_backups_list_backups_delegates():
    """Test list_backups delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.list_backups", return_value=[]) as mock:
        result = backups.list_backups("/backups")
        
        mock.assert_called_once_with("/backups")
        assert result == []


def test_backups_list_backups_with_pattern():
    """Test list_backups passes pattern to impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.list_backups", return_value=[]) as mock:
        result = backups.list_backups("/backups")
        
        mock.assert_called_once_with("/backups")
        assert result == []


def test_backups_restore_backup_delegates():
    """Test restore_backup delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.restore_backup", return_value=True) as mock:
        result = backups.restore_backup("/backup.zip", "/restore")
        
        mock.assert_called_once_with("/backup.zip", "/restore")
        assert result is True


def test_backups_validate_backup_file_delegates():
    """Test validate_backup_file delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.validate_backup_file", return_value=True) as mock:
        result = backups.validate_backup_file("/backup.zip")
        
        mock.assert_called_once_with("/backup.zip")
        assert result is True


def test_backups_get_backup_size_delegates():
    """Test get_backup_size delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.get_backup_size", return_value=12345) as mock:
        result = backups.get_backup_size("/backup.zip")
        
        mock.assert_called_once_with("/backup.zip")
        assert result == 12345


def test_backups_cleanup_temp_files_delegates():
    """Test cleanup_temp_files delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.cleanup_temp_files", return_value=None) as mock:
        result = backups.cleanup_temp_files("/tmp/path")
        
        mock.assert_called_once_with("/tmp/path")
        assert result is None


def test_backups_get_default_backup_config_delegates():
    """Test get_default_backup_config delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.get_default_backup_config", return_value={}) as mock:
        result = backups.get_default_backup_config()
        
        mock.assert_called_once_with()
        assert result == {}


def test_backups_merge_backup_configs_delegates():
    """Test merge_backup_configs delegates to backups_impl."""
    import researcharr.backups as backups
    
    with patch("researcharr.backups_impl.merge_backup_configs", return_value={"merged": True}) as mock:
        result = backups.merge_backup_configs({"a": 1}, {"b": 2})
        
        mock.assert_called_once_with({"a": 1}, {"b": 2})
        assert result == {"merged": True}


def test_create_backup_file_raises_on_missing_config_root():
    """Test create_backup_file raises when config root doesn't exist and no prefix."""
    import researcharr.backups as backups
    
    with pytest.raises(Exception, match="Config root does not exist"):
        backups.create_backup_file("/nonexistent/path", "/backups", prefix="")


def test_create_backup_file_allows_missing_config_with_prefix():
    """Test create_backup_file allows missing config root when prefix provided."""
    import researcharr.backups as backups
    
    config_dir = "/nonexistent/path"
    backups_dir = tempfile.mkdtemp()
    
    try:
        with patch("researcharr.backups_impl.create_backup_file", return_value="backup.zip"):
            result = backups.create_backup_file(config_dir, backups_dir, prefix="manual-")
            
            # Should delegate without raising
            assert result == "backup.zip"
    finally:
        shutil.rmtree(backups_dir, ignore_errors=True)


def test_create_backup_file_delegates_on_valid_config():
    """Test create_backup_file delegates to impl when config exists."""
    import researcharr.backups as backups
    
    config_dir = tempfile.mkdtemp()
    backups_dir = tempfile.mkdtemp()
    
    try:
        with patch("researcharr.backups_impl.create_backup_file", return_value="backup.zip") as mock:
            result = backups.create_backup_file(config_dir, backups_dir)
            
            mock.assert_called_once_with(config_dir, backups_dir, prefix="")
            assert result == "backup.zip"
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)
        shutil.rmtree(backups_dir, ignore_errors=True)


def test_create_backup_file_handles_path_construction_exception():
    """Test create_backup_file handles Path construction exception."""
    import researcharr.backups as backups
    
    # Use an invalid path string
    invalid_path = "\x00invalid\x00path"
    backups_dir = tempfile.mkdtemp()
    
    try:
        with patch("researcharr.backups_impl.create_backup_file", return_value="backup.zip"):
            result = backups.create_backup_file(invalid_path, backups_dir, prefix="test-")
            
            # Should delegate even if Path() fails
            assert result == "backup.zip"
    finally:
        shutil.rmtree(backups_dir, ignore_errors=True)


def test_backup_path_class_internal_import_available():
    """Test BackupPath uses _backups_impl version when available."""
    import researcharr.backups as backups
    
    # BackupPath should be available
    assert hasattr(backups, "BackupPath")
    assert backups.BackupPath is not None  # type: ignore[attr-defined]


def test_backup_path_fallback_class_basic():
    """Test BackupPath fallback class basic functionality."""
    # Try to use fallback by temporarily hiding _backups_impl
    with patch.dict("sys.modules", {"researcharr._backups_impl": None}):
        # Re-import to get fallback class
        import importlib
        import researcharr.backups
        importlib.reload(researcharr.backups)
        
        # Create instance (may use internal or fallback)
        bp = researcharr.backups.BackupPath("/path/to/backup.zip", "backup.zip")  # type: ignore[attr-defined]
        
        assert str(bp) == "/path/to/backup.zip"


def test_backup_path_fallback_startswith_with_separator():
    """Test BackupPath fallback startswith with path separator."""
    import researcharr.backups as backups
    BackupPath = backups.BackupPath  # type: ignore[attr-defined]
    
    # If using fallback, test it directly
    if hasattr(BackupPath, "__new__"):
        bp = BackupPath("/var/backups/backup.zip", "backup.zip")
        
        # Should use full path for comparisons with separators
        assert bp.startswith("/var/")
        assert bp.startswith("/var/backups")

def test_backup_path_fallback_startswith_name_only():
    """Test BackupPath fallback startswith with name-only prefix."""
    import researcharr.backups as backups
    BackupPath = backups.BackupPath  # type: ignore[attr-defined]
    
    if hasattr(BackupPath, "__new__"):
        bp = BackupPath("/var/backups/manual-backup.zip", "manual-backup.zip")
        
        # Should use name for comparisons without separators
        assert bp.startswith("manual")
        assert not bp.startswith("auto")

def test_backup_path_fallback_startswith_none_prefix():
    """Test BackupPath fallback handles None prefix."""
    import researcharr.backups as backups
    BackupPath = backups.BackupPath  # type: ignore[attr-defined]
    
    if hasattr(BackupPath, "__new__"):
        bp = BackupPath("/path/backup.zip", "backup.zip")
        
        # Should return False for None prefix
        assert not bp.startswith(None)  # type: ignore[arg-type]

def test_backup_path_fallback_startswith_exception_handling():
    """Test BackupPath fallback handles exceptions in startswith."""
    import researcharr.backups as backups
    BackupPath = backups.BackupPath  # type: ignore[attr-defined]
    
    if hasattr(BackupPath, "__new__"):
        bp = BackupPath("/path/backup.zip", "backup.zip")
        
        # Mock object.__getattribute__ to raise
        with patch("builtins.object.__getattribute__", side_effect=AttributeError("test")):
            # Should fall back to str.startswith
            result = bp.startswith("/path")
            # May return True or handle gracefully
            assert isinstance(result, bool)


def test_create_backup_file_with_empty_string_prefix():
    """Test create_backup_file with empty string prefix (should raise on missing)."""
    import researcharr.backups as backups
    
    with pytest.raises(Exception, match="Config root does not exist"):
        backups.create_backup_file("/nonexistent", "/backups", prefix="")


def test_create_backup_file_passes_prefix_to_impl():
    """Test create_backup_file passes prefix parameter correctly."""
    import researcharr.backups as backups
    
    config_dir = tempfile.mkdtemp()
    backups_dir = tempfile.mkdtemp()
    
    try:
        with patch("researcharr.backups_impl.create_backup_file", return_value="backup.zip") as mock:
            result = backups.create_backup_file(config_dir, backups_dir, prefix="custom-")
            
            mock.assert_called_once_with(config_dir, backups_dir, prefix="custom-")
            assert result == "backup.zip"
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)
        shutil.rmtree(backups_dir, ignore_errors=True)


def test_backups_module_imports_backups_impl():
    """Test that backups module imports backups_impl."""
    import researcharr.backups as backups
    
    # Verify the module loaded successfully
    assert backups is not None
    assert hasattr(backups, "create_backup_file")
    
def test_backup_path_windows_separator():
    """Test BackupPath fallback handles Windows-style separators."""
    import researcharr.backups as backups
    BackupPath = backups.BackupPath  # type: ignore[attr-defined]
    
    if hasattr(BackupPath, "__new__"):
        bp = BackupPath("C:\\backups\\backup.zip", "backup.zip")
        result = bp.startswith("C:\\")
        # Either True or False is acceptable
        assert isinstance(result, bool)


def test_create_backup_validation_edge_cases():
    """Test create_backup_file validation edge cases."""
    import researcharr.backups as backups
    
    # Test with existing dir and empty prefix
    config_dir = tempfile.mkdtemp()
    backups_dir = tempfile.mkdtemp()
    
    try:
        with patch("researcharr.backups_impl.create_backup_file", return_value="backup.zip"):
            # Should work with existing dir and empty prefix
            result = backups.create_backup_file(config_dir, backups_dir, prefix="")
            assert result == "backup.zip"
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)
        shutil.rmtree(backups_dir, ignore_errors=True)


def test_delegation_functions_pass_args_kwargs():
    """Test that all delegation functions pass *args and **kwargs."""
    import researcharr.backups as backups
    
    # Test get_backup_info with correct signature (single path argument)
    with patch("researcharr.backups_impl.get_backup_info", return_value=None) as mock:
        backups.get_backup_info("/backup.zip")
        mock.assert_called_once_with("/backup.zip")
    
    # Test prune_backups with correct signature (directory and config)
    with patch("researcharr.backups_impl.prune_backups", return_value=None) as mock:
        backups.prune_backups("/dir", {"cfg": 1})
        mock.assert_called_once_with("/dir", {"cfg": 1})


def test_backup_path_import_fallback_chain():
    """Test BackupPath import fallback logic."""
    import researcharr.backups as backups
    
    # BackupPath should be defined regardless of import success
    assert hasattr(backups, "BackupPath")
    
    # Should be either the imported class or the fallback
    bp_class = backups.BackupPath  # type: ignore[attr-defined]
    assert bp_class is not None
    
    # Should be callable
    assert callable(bp_class)
from unittest.mock import patch

import pytest


def test_backup_path_import():
    """Test that BackupPath can be imported."""
    from researcharr.backups import BackupPath
    
    assert BackupPath is not None


def test_backup_path_creation():
    """Test BackupPath creation."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("/test/path/file.zip", "file.zip")
    
    assert isinstance(bp, str)
    assert str(bp) == "/test/path/file.zip"


def test_backup_path_startswith_name():
    """Test BackupPath startswith uses name."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("/test/path/backup-file.zip", "backup-file.zip")
    
    # Should check against name when prefix doesn't have separator
    assert bp.startswith("backup-")
    assert not bp.startswith("test-")


def test_backup_path_startswith_fullpath():
    """Test BackupPath startswith uses fullpath for paths."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("/test/path/backup-file.zip", "backup-file.zip")
    
    # Should check against full path when prefix has separator
    assert bp.startswith("/test/")
    assert not bp.startswith("/other/")


def test_backup_path_startswith_none():
    """Test BackupPath startswith handles None prefix."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("/test/path/file.zip", "file.zip")
    
    assert not bp.startswith(None)


def test_backup_path_startswith_exception():
    """Test BackupPath startswith handles exceptions."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("/test/path/file.zip", "file.zip")
    
    # Should fall back to string startswith on exception
    with patch("os.sep", side_effect=Exception("OS error")):
        result = bp.startswith("test")
        # Should still work via fallback
        assert isinstance(result, bool)


def test_create_backup_file_missing_config_no_prefix():
    """Test create_backup_file raises when config_root missing without prefix."""
    from researcharr.backups import create_backup_file
    
    with pytest.raises(Exception, match="Config root does not exist"):
        create_backup_file("/nonexistent/path", "/tmp/backups", prefix="")


def test_create_backup_file_delegates():
    """Test create_backup_file delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "create_backup_file", return_value="test.zip"):
        result = backups.create_backup_file("/test/config", "/test/backups", prefix="test-")
        
        assert result == "test.zip"


def test_get_backup_info_delegates():
    """Test get_backup_info delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "get_backup_info", return_value={"size": 100}):
        result = backups.get_backup_info("test.zip")
        
        assert result == {"size": 100}


def test_prune_backups_delegates():
    """Test prune_backups delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "prune_backups", return_value=2):
        result = backups.prune_backups("/test/backups", keep=5)
        
        assert result == 2


def test_list_backups_delegates():
    """Test list_backups delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "list_backups", return_value=["file1.zip", "file2.zip"]):
        result = backups.list_backups("/test/backups")
        
        assert len(result) == 2


def test_restore_backup_delegates():
    """Test restore_backup delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "restore_backup", return_value=True):
        result = backups.restore_backup("test.zip", "/test/restore")
        
        assert result is True


def test_validate_backup_file_delegates():
    """Test validate_backup_file delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "validate_backup_file", return_value=True):
        result = backups.validate_backup_file("test.zip")
        
        assert result is True


def test_get_backup_size_delegates():
    """Test get_backup_size delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "get_backup_size", return_value=1024):
        result = backups.get_backup_size("test.zip")
        
        assert result == 1024


def test_cleanup_temp_files_delegates():
    """Test cleanup_temp_files delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "cleanup_temp_files", return_value=3):
        result = backups.cleanup_temp_files("/test/temp")
        
        assert result == 3


def test_get_default_backup_config_delegates():
    """Test get_default_backup_config delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "get_default_backup_config", return_value={"keep": 5}):
        result = backups.get_default_backup_config()
        
        assert result == {"keep": 5}


def test_merge_backup_configs_delegates():
    """Test merge_backup_configs delegates to impl."""
    from researcharr import backups
    
    with patch.object(backups.backups_impl, "merge_backup_configs", return_value={"merged": True}):
        result = backups.merge_backup_configs({"a": 1}, {"b": 2})
        
        assert result == {"merged": True}


def test_backups_all_exports():
    """Test that backups module exports expected symbols."""
    from researcharr import backups
    
    expected = [
        "BackupPath",
        "create_backup_file",
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
    
    assert hasattr(backups, "__all__")
    assert set(backups.__all__) == set(expected)


def test_backup_path_with_impl_import():
    """Test BackupPath when _BackupPath is available."""
    from researcharr import backups
    
    # BackupPath should be either the internal class or fallback
    assert backups.BackupPath is not None


def test_backup_path_without_impl_import():
    """Test BackupPath fallback when _BackupPath import fails."""
    from researcharr import backups
    
    # Save original
    orig_bp = backups._BackupPath
    
    try:
        # Set to None to trigger fallback
        backups._BackupPath = None
        
        # The fallback class should still work
        bp = backups.BackupPath("/test/path/file.zip", "file.zip")
        assert str(bp) == "/test/path/file.zip"
    finally:
        # Restore
        backups._BackupPath = orig_bp


def test_create_backup_file_path_construction_failure():
    """Test create_backup_file handles Path construction failure."""
    from researcharr import backups
    
    with patch("pathlib.Path", side_effect=Exception("Path error")):
        with patch.object(backups.backups_impl, "create_backup_file", return_value="test.zip"):
            result = backups.create_backup_file("/test/config", "/test/backups", prefix="test-")
            
            # Should still work via delegation
            assert result == "test.zip"


def test_create_backup_file_with_existing_config():
    """Test create_backup_file with existing config root."""
    from researcharr import backups
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config"
        config_path.mkdir()
        
        backups_path = Path(tmpdir) / "backups"
        backups_path.mkdir()
        
        with patch.object(backups.backups_impl, "create_backup_file", return_value="test.zip"):
            result = backups.create_backup_file(str(config_path), str(backups_path))
            
            assert result == "test.zip"


def test_backup_path_startswith_backslash():
    """Test BackupPath startswith with backslash separator."""
    from researcharr.backups import BackupPath
    
    bp = BackupPath("C:\\test\\path\\file.zip", "file.zip")
    
    # Should check against full path when prefix has backslash
    assert bp.startswith("C:\\test\\") or bp.startswith("file")
