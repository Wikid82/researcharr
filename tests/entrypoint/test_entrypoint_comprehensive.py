"""Comprehensive tests for entrypoint.py module to maximize coverage."""

import logging
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from flask import Flask

# Import the module under test (package import to avoid CWD issues in CI)
from researcharr import entrypoint

# Import test utilities for logging isolation
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.logging
class TestEntrypointModule(unittest.TestCase):
    """Comprehensive test cases for entrypoint.py module.

    Uses LoggerTestHelper to ensure proper logging isolation and prevent
    test pollution that can break pytest's caplog fixture.
    """

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test_researcharr.db")
        self.test_log_path = os.path.join(self.test_dir, "test.log")
        # Track logger helpers for cleanup
        self._logger_helpers = []

    def tearDown(self):
        """Clean up test environment with proper logging state restoration."""
        import shutil

        # Clean up logger helpers (ensures proper state restoration)
        for helper in self._logger_helpers:
            helper.cleanup()

        # Additional cleanup for any direct logger manipulations
        logger = logging.getLogger("test_logger")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_module_constants(self):
        """Test module-level constants."""
        self.assertEqual(entrypoint.DB_PATH, "researcharr.db")
        self.assertIsInstance(entrypoint.__path__, list)
        self.assertEqual(len(entrypoint.__path__), 2)

    def test_conditional_imports_exist(self):
        """Test that conditional imports are working."""
        # requests and yaml should be imported
        self.assertTrue(hasattr(entrypoint, "requests"))
        self.assertTrue(hasattr(entrypoint, "yaml"))

    def test_init_db_default_path(self):
        """Test database initialization with default path."""
        with patch("entrypoint.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            entrypoint.init_db()

            mock_connect.assert_called_with(entrypoint.DB_PATH)
            # Should create both tables
            self.assertEqual(mock_cursor.execute.call_count, 2)
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_init_db_custom_path(self):
        """Test database initialization with custom path."""
        custom_path = "/custom/path/test.db"

        with patch("entrypoint.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            entrypoint.init_db(custom_path)

            mock_connect.assert_called_with(custom_path)
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_init_db_actual_database(self):
        """Test actual database creation (integration test)."""
        entrypoint.init_db(self.test_db_path)

        # Verify database file was created
        self.assertTrue(os.path.exists(self.test_db_path))

        # Verify tables were created
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # Check radarr_queue table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='radarr_queue'")
        self.assertIsNotNone(cursor.fetchone())

        # Check sonarr_queue table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sonarr_queue'")
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def test_setup_logger_new_logger(self):
        """Test setting up a new logger."""
        logger = entrypoint.setup_logger("test_logger", self.test_log_path)

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_logger")
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.FileHandler)

    def test_setup_logger_with_custom_level(self):
        """Test setting up logger with custom level."""
        logger = entrypoint.setup_logger("test_logger_debug", self.test_log_path, logging.DEBUG)

        self.assertEqual(logger.level, logging.DEBUG)

    def test_setup_logger_existing_logger(self):
        """Test that existing logger doesn't get duplicate handlers."""
        # Create logger first time
        logger1 = entrypoint.setup_logger("existing_logger", self.test_log_path)
        handler_count = len(logger1.handlers)

        # Create same logger again
        logger2 = entrypoint.setup_logger("existing_logger", self.test_log_path)

        # Should be same logger instance with same number of handlers
        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger2.handlers), handler_count)

    def test_setup_logger_with_none_level(self):
        """Test setup_logger with None level defaults to INFO."""
        logger = entrypoint.setup_logger("test_logger_none", self.test_log_path, None)
        self.assertEqual(logger.level, logging.INFO)

    def test_has_valid_url_and_key_all_valid(self):
        """Test has_valid_url_and_key with all valid instances."""
        instances = [
            {"enabled": True, "url": "http://example.com", "api_key": "test_key"},
            {"enabled": False, "url": "", "api_key": ""},  # disabled, so valid
            {"enabled": True, "url": "https://test.com", "api_key": "another_key"},
        ]

        result = entrypoint.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_invalid_url(self):
        """Test has_valid_url_and_key with invalid URL."""
        instances = [
            {"enabled": True, "url": "ftp://bad.com", "api_key": "test_key"}  # ftp not http/https
        ]

        result = entrypoint.has_valid_url_and_key(instances)
        self.assertFalse(result)

    def test_has_valid_url_and_key_missing_api_key(self):
        """Test has_valid_url_and_key with missing API key."""
        instances = [{"enabled": True, "url": "http://example.com", "api_key": ""}]

        result = entrypoint.has_valid_url_and_key(instances)
        self.assertFalse(result)

    def test_has_valid_url_and_key_disabled_invalid(self):
        """Test has_valid_url_and_key with disabled instances (should be valid)."""
        instances = [
            {
                "enabled": False,
                "url": "invalid",
                "api_key": "",
            }  # disabled, so valid even if invalid
        ]

        result = entrypoint.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_empty_list(self):
        """Test has_valid_url_and_key with empty list."""
        result = entrypoint.has_valid_url_and_key([])
        self.assertTrue(result)  # all() returns True for empty iterable

    def test_check_radarr_connection_missing_url(self):
        """Test Radarr connection check with missing URL."""
        logger = Mock()

        result = entrypoint.check_radarr_connection("", "api_key", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Radarr URL or API key")

    def test_check_radarr_connection_missing_api_key(self):
        """Test Radarr connection check with missing API key."""
        logger = Mock()

        result = entrypoint.check_radarr_connection("http://example.com", "", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Radarr URL or API key")

    @patch("entrypoint.requests.get")
    def test_check_radarr_connection_success(self, mock_get):
        """Test successful Radarr connection."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = entrypoint.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertTrue(result)
        logger.info.assert_called_with("Radarr connection successful.")

    @patch("entrypoint.requests.get")
    def test_check_radarr_connection_non_200_status(self, mock_get):
        """Test Radarr connection with non-200 status."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = entrypoint.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Radarr connection failed with status %s", 404)

    @patch("entrypoint.requests.get")
    def test_check_radarr_connection_exception(self, mock_get):
        """Test Radarr connection with request exception."""
        logger = Mock()
        mock_get.side_effect = Exception("Connection error")

        result = entrypoint.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Radarr connection failed: %s", mock_get.side_effect)

    def test_check_sonarr_connection_missing_url(self):
        """Test Sonarr connection check with missing URL."""
        logger = Mock()

        result = entrypoint.check_sonarr_connection("", "api_key", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Sonarr URL or API key")

    def test_check_sonarr_connection_missing_api_key(self):
        """Test Sonarr connection check with missing API key."""
        logger = Mock()

        result = entrypoint.check_sonarr_connection("http://example.com", "", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Sonarr URL or API key")

    @patch("entrypoint.requests.get")
    def test_check_sonarr_connection_success(self, mock_get):
        """Test successful Sonarr connection."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = entrypoint.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertTrue(result)
        logger.info.assert_called_with("Sonarr connection successful.")

    @patch("entrypoint.requests.get")
    def test_check_sonarr_connection_non_200_status(self, mock_get):
        """Test Sonarr connection with non-200 status."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = entrypoint.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Sonarr connection failed with status %s", 500)

    @patch("entrypoint.requests.get")
    def test_check_sonarr_connection_exception(self, mock_get):
        """Test Sonarr connection with request exception."""
        logger = Mock()
        mock_get.side_effect = Exception("Network error")

        result = entrypoint.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Sonarr connection failed: %s", mock_get.side_effect)

    def test_load_config_missing_file(self):
        """Test loading config with missing file."""
        with self.assertRaises(FileNotFoundError):
            entrypoint.load_config("nonexistent.yml")

    @patch("builtins.open", new_callable=mock_open, read_data="key: value\nother: data")
    @patch("entrypoint.os.path.exists")
    def test_load_config_valid_file(self, mock_exists, mock_file):
        """Test loading valid config file."""
        mock_exists.return_value = True

        with patch("entrypoint.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {"key": "value", "other": "data"}

            result = entrypoint.load_config("test.yml")

            self.assertEqual(result, {"key": "value", "other": "data"})
            mock_file.assert_called_with("test.yml")

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("entrypoint.os.path.exists")
    def test_load_config_empty_file(self, mock_exists, mock_file):
        """Test loading empty config file."""
        mock_exists.return_value = True

        with patch("entrypoint.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = None

            result = entrypoint.load_config("empty.yml")

            self.assertEqual(result, {})

    def test_create_metrics_app(self):
        """Test creating metrics Flask app."""
        app = entrypoint.create_metrics_app()

        self.assertIsInstance(app, Flask)
        self.assertEqual(app.name, "metrics")
        self.assertTrue(hasattr(app, "metrics"))
        self.assertEqual(app.metrics["requests_total"], 0)
        self.assertEqual(app.metrics["errors_total"], 0)

    def test_create_metrics_app_health_endpoint(self):
        """Test metrics app health endpoint."""
        app = entrypoint.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("status", data)
            self.assertIn("db", data)
            self.assertIn("config", data)

    def test_create_metrics_app_health_endpoint_db_error(self):
        """Test health endpoint when database connection fails."""
        app = entrypoint.create_metrics_app()

        with patch("entrypoint.sqlite3.connect", side_effect=Exception("DB Error")):
            with app.test_client() as client:
                response = client.get("/health")

                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["db"], "error")

    def test_create_metrics_app_metrics_endpoint(self):
        """Test metrics app metrics endpoint."""
        app = entrypoint.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/metrics")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("requests_total", data)
            self.assertIn("errors_total", data)

    def test_create_metrics_app_request_counter(self):
        """Test that requests are counted properly."""
        app = entrypoint.create_metrics_app()

        with app.test_client() as client:
            # Make a few requests
            client.get("/health")
            client.get("/metrics")

            response = client.get("/metrics")
            data = response.get_json()

            # Should count all 3 requests (including the final metrics call)
            self.assertEqual(data["requests_total"], 3)

    def test_create_metrics_app_error_handler_404(self):
        """Test 404 error handler."""
        app = entrypoint.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/nonexistent")

            self.assertEqual(response.status_code, 500)  # Error handler converts to 500
            data = response.get_json()
            self.assertIn("error", data)

    def test_create_metrics_app_error_handler_500(self):
        """Test 500 error handler."""
        app = entrypoint.create_metrics_app()

        # Add a route that raises an exception
        @app.route("/test-error")
        def test_error():
            raise Exception("Test error")

        with app.test_client() as client:
            response = client.get("/test-error")

            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertIn("error", data)

    def test_create_metrics_app_error_counter(self):
        """Test that errors are counted properly."""
        app = entrypoint.create_metrics_app()

        with app.test_client() as client:
            # Trigger some errors
            client.get("/nonexistent")
            client.get("/another-nonexistent")

            response = client.get("/metrics")
            data = response.get_json()

            # Should count the 2 errors
            self.assertEqual(data["errors_total"], 2)

    def test_path_attribute_structure(self):
        """Test __path__ attribute structure."""
        self.assertIsInstance(entrypoint.__path__, list)
        self.assertEqual(len(entrypoint.__path__), 2)

        # First should be current directory
        self.assertTrue(
            entrypoint.__path__[0].endswith("/researcharr")
            or entrypoint.__path__[0] == os.path.dirname(entrypoint.__file__)
        )

        # Second should be researcharr subdirectory
        self.assertTrue("researcharr" in entrypoint.__path__[1])


if __name__ == "__main__":
    unittest.main()
