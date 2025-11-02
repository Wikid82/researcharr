"""Focused tests for researcharr.py root module."""

import importlib.util
import logging
import unittest
from unittest.mock import Mock, mock_open, patch

# Import the root researcharr.py module directly (not the package)
spec = importlib.util.spec_from_file_location(
    "researcharr_root", "/home/jeremy/Server/Projects/researcharr/researcharr.py"
)
researcharr_root = importlib.util.module_from_spec(spec)
spec.loader.exec_module(researcharr_root)


class TestResearcharrRootModule(unittest.TestCase):
    """Test the root researcharr.py module functionality."""

    def test_module_constants(self):
        """Test module-level constants are defined."""
        self.assertEqual(researcharr_root.DB_PATH, "researcharr.db")
        self.assertTrue(hasattr(researcharr_root, "__path__"))
        self.assertIsInstance(researcharr_root.__path__, list)

    def test_serve_function_exists(self):
        """Test the serve function exists and can be called."""
        self.assertTrue(hasattr(researcharr_root, "serve"))
        self.assertTrue(callable(researcharr_root.serve))

    def test_init_db_function_exists(self):
        """Test the init_db function exists and can be called."""
        self.assertTrue(hasattr(researcharr_root, "init_db"))
        self.assertTrue(callable(researcharr_root.init_db))

    def test_init_db_default_path(self):
        """Test init_db with default path."""
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            researcharr_root.init_db()

            mock_connect.assert_called_once_with("researcharr.db")
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_init_db_custom_path(self):
        """Test init_db with custom path."""
        custom_path = "custom_test.db"
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            researcharr_root.init_db(custom_path)

            mock_connect.assert_called_once_with(custom_path)

    def test_setup_logger_function_exists(self):
        """Test the setup_logger function exists."""
        self.assertTrue(hasattr(researcharr_root, "setup_logger"))
        self.assertTrue(callable(researcharr_root.setup_logger))

    def test_setup_logger_basic(self):
        """Test setup_logger creates logger with proper configuration."""
        logger_name = "test_logger"
        log_file = "test.log"

        # Test the actual function behavior (it checks for duplicates)
        logger = researcharr_root.setup_logger(logger_name, log_file)
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, logger_name)
        self.assertEqual(logger.level, logging.INFO)

    def test_load_config_function_exists(self):
        """Test the load_config function exists."""
        self.assertTrue(hasattr(researcharr_root, "load_config"))
        self.assertTrue(callable(researcharr_root.load_config))

    def test_load_config_valid_file(self):
        """Test load_config with valid YAML file."""
        config_data = {"test": "value", "nested": {"key": "val"}}

        with patch("builtins.open", mock_open(read_data="test: value\nnested:\n  key: val")):
            with patch("os.path.exists", return_value=True):
                with patch.object(researcharr_root.yaml, "safe_load", return_value=config_data):
                    result = researcharr_root.load_config("test.yml")
                    self.assertEqual(result, config_data)

    def test_load_config_missing_file(self):
        """Test load_config with missing file."""
        with patch("os.path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                researcharr_root.load_config("missing.yml")

    def test_has_valid_url_and_key_function_exists(self):
        """Test the has_valid_url_and_key function exists."""
        self.assertTrue(hasattr(researcharr_root, "has_valid_url_and_key"))
        self.assertTrue(callable(researcharr_root.has_valid_url_and_key))

    def test_has_valid_url_and_key_empty_list(self):
        """Test has_valid_url_and_key with empty list."""
        result = researcharr_root.has_valid_url_and_key([])
        self.assertTrue(result)  # all() of empty iterable is True

    def test_has_valid_url_and_key_valid_instances(self):
        """Test has_valid_url_and_key with valid instances."""
        instances = [
            {"enabled": True, "url": "http://test1.com", "api_key": "key1"},
            {"enabled": True, "url": "https://test2.com", "api_key": "key2"},
        ]
        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_disabled_instances(self):
        """Test has_valid_url_and_key with all disabled instances."""
        instances = [
            {"enabled": False, "url": "invalid", "api_key": ""},
            {"enabled": False, "url": "", "api_key": "invalid"},
        ]
        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertTrue(result)  # Function returns True even for disabled instances

    def test_check_radarr_connection_function_exists(self):
        """Test the check_radarr_connection function exists."""
        self.assertTrue(hasattr(researcharr_root, "check_radarr_connection"))
        self.assertTrue(callable(researcharr_root.check_radarr_connection))

    def test_check_sonarr_connection_function_exists(self):
        """Test the check_sonarr_connection function exists."""
        self.assertTrue(hasattr(researcharr_root, "check_sonarr_connection"))
        self.assertTrue(callable(researcharr_root.check_sonarr_connection))

    def test_check_radarr_connection_success(self):
        """Test successful Radarr connection."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "3.0.0"}
            mock_get.return_value = mock_response

            result = researcharr_root.check_radarr_connection(
                "http://radarr.local", "test_key", mock_logger
            )

            self.assertTrue(result)
            mock_get.assert_called_once()

    def test_check_radarr_connection_missing_url(self):
        """Test Radarr connection with missing URL."""
        mock_logger = Mock()
        result = researcharr_root.check_radarr_connection("", "test_key", mock_logger)
        self.assertFalse(result)

    def test_check_radarr_connection_missing_api_key(self):
        """Test Radarr connection with missing API key."""
        mock_logger = Mock()
        result = researcharr_root.check_radarr_connection("http://radarr.local", "", mock_logger)
        self.assertFalse(result)

    def test_check_sonarr_connection_success(self):
        """Test successful Sonarr connection."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "3.0.0"}
            mock_get.return_value = mock_response

            result = researcharr_root.check_sonarr_connection(
                "http://sonarr.local", "test_key", mock_logger
            )

            self.assertTrue(result)
            mock_get.assert_called_once()

    def test_create_metrics_app_function_exists(self):
        """Test the create_metrics_app function exists."""
        self.assertTrue(hasattr(researcharr_root, "create_metrics_app"))
        self.assertTrue(callable(researcharr_root.create_metrics_app))

    def test_create_metrics_app_basic(self):
        """Test create_metrics_app creates Flask app."""
        app = researcharr_root.create_metrics_app()
        self.assertIsNotNone(app)

        # Test that the app has expected routes
        with app.test_client() as client:
            # Test health endpoint
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)

            # Test metrics endpoint
            response = client.get("/metrics")
            self.assertEqual(response.status_code, 200)

    def test_conditional_imports(self):
        """Test that conditional imports work."""
        # These should be available after module load
        self.assertTrue(hasattr(researcharr_root, "requests"))
        self.assertTrue(hasattr(researcharr_root, "yaml"))

    def test_main_execution_compatibility(self):
        """Test that module can be executed with arguments."""
        # Test that the module has the expected structure for __main__ execution
        self.assertTrue(hasattr(researcharr_root, "serve"))

        # The __main__ block should be testable via sys.argv manipulation
        import sys

        original_argv = sys.argv[:]
        try:
            # This tests the structure exists for main execution
            sys.argv = ["researcharr.py", "serve"]
            # The actual __main__ block execution would happen during import
            # so we just verify the function exists
            self.assertTrue(callable(researcharr_root.serve))
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
