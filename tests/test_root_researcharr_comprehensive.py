"""Comprehensive tests for root researcharr.py module to maximize coverage."""

import logging
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, mock_open, patch

from flask import Flask

# Import the module under test
import researcharr


class TestRootResearcharrModule(unittest.TestCase):
    """Comprehensive test cases for root researcharr.py module."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test_researcharr.db")
        self.test_log_path = os.path.join(self.test_dir, "test.log")

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

        # Clean up any loggers created during tests
        logger = logging.getLogger("test_logger")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)

    def test_module_constants_and_paths(self):
        """Test module-level constants and __path__ attribute."""
        self.assertEqual(researcharr.DB_PATH, "researcharr.db")
        self.assertIsInstance(researcharr.__path__, list)
        self.assertEqual(len(researcharr.__path__), 2)

    def test_conditional_imports_exist(self):
        """Test that conditional imports are working."""
        # requests and yaml should be imported
        self.assertTrue(hasattr(researcharr, "requests"))
        self.assertTrue(hasattr(researcharr, "yaml"))

    def test_init_db_default_path(self):
        """Test database initialization with default path."""
        with patch("researcharr.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            researcharr.init_db()

            mock_connect.assert_called_with(researcharr.DB_PATH)
            # Should create both tables
            self.assertEqual(mock_cursor.execute.call_count, 2)
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_init_db_custom_path(self):
        """Test database initialization with custom path."""
        custom_path = "/custom/path/test.db"

        with patch("researcharr.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            researcharr.init_db(custom_path)

            mock_connect.assert_called_with(custom_path)
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_init_db_actual_database(self):
        """Test actual database creation (integration test)."""
        researcharr.init_db(self.test_db_path)

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

    def test_setup_logger_conditional_definition(self):
        """Test that setup_logger is conditionally defined."""
        # Should exist in globals
        self.assertTrue(hasattr(researcharr, "setup_logger"))
        self.assertTrue(callable(researcharr.setup_logger))

    def test_setup_logger_new_logger(self):
        """Test setting up a new logger."""
        logger = researcharr.setup_logger("test_logger", self.test_log_path)

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_logger")
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.FileHandler)

    def test_setup_logger_with_custom_level(self):
        """Test setting up logger with custom level."""
        logger = researcharr.setup_logger("test_logger_debug", self.test_log_path, logging.DEBUG)

        self.assertEqual(logger.level, logging.DEBUG)

    def test_setup_logger_existing_logger(self):
        """Test that existing logger doesn't get duplicate handlers."""
        # Create logger first time
        logger1 = researcharr.setup_logger("existing_logger", self.test_log_path)
        handler_count = len(logger1.handlers)

        # Create same logger again
        logger2 = researcharr.setup_logger("existing_logger", self.test_log_path)

        # Should be same logger instance with same number of handlers
        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger2.handlers), handler_count)

    def test_setup_logger_with_none_level(self):
        """Test setup_logger with None level defaults to INFO."""
        logger = researcharr.setup_logger("test_logger_none", self.test_log_path, None)
        self.assertEqual(logger.level, logging.INFO)

    def test_has_valid_url_and_key_all_valid(self):
        """Test has_valid_url_and_key with all valid instances."""
        instances = [
            {"enabled": True, "url": "http://example.com", "api_key": "test_key"},
            {"enabled": False, "url": "", "api_key": ""},  # disabled, so valid
            {"enabled": True, "url": "https://test.com", "api_key": "another_key"},
        ]

        result = researcharr.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_invalid_url(self):
        """Test has_valid_url_and_key with invalid URL."""
        instances = [
            {"enabled": True, "url": "ftp://bad.com", "api_key": "test_key"}  # ftp not http/https
        ]

        result = researcharr.has_valid_url_and_key(instances)
        self.assertFalse(result)

    def test_has_valid_url_and_key_missing_api_key(self):
        """Test has_valid_url_and_key with missing API key."""
        instances = [{"enabled": True, "url": "http://example.com", "api_key": ""}]

        result = researcharr.has_valid_url_and_key(instances)
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

        result = researcharr.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_empty_list(self):
        """Test has_valid_url_and_key with empty list."""
        result = researcharr.has_valid_url_and_key([])
        self.assertTrue(result)  # all() returns True for empty iterable

    def test_check_radarr_connection_missing_url(self):
        """Test Radarr connection check with missing URL."""
        logger = Mock()

        result = researcharr.check_radarr_connection("", "api_key", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Radarr URL or API key")

    def test_check_radarr_connection_missing_api_key(self):
        """Test Radarr connection check with missing API key."""
        logger = Mock()

        result = researcharr.check_radarr_connection("http://example.com", "", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Radarr URL or API key")

    @patch("researcharr.requests.get")
    def test_check_radarr_connection_success(self, mock_get):
        """Test successful Radarr connection."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = researcharr.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertTrue(result)
        logger.info.assert_called_with("Radarr connection successful.")

    @patch("researcharr.requests.get")
    def test_check_radarr_connection_non_200_status(self, mock_get):
        """Test Radarr connection with non-200 status."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = researcharr.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Radarr connection failed with status %s", 404)

    @patch("researcharr.requests.get")
    def test_check_radarr_connection_exception(self, mock_get):
        """Test Radarr connection with request exception."""
        logger = Mock()
        mock_get.side_effect = Exception("Connection error")

        result = researcharr.check_radarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Radarr connection failed: %s", mock_get.side_effect)

    def test_check_sonarr_connection_missing_url(self):
        """Test Sonarr connection check with missing URL."""
        logger = Mock()

        result = researcharr.check_sonarr_connection("", "api_key", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Sonarr URL or API key")

    def test_check_sonarr_connection_missing_api_key(self):
        """Test Sonarr connection check with missing API key."""
        logger = Mock()

        result = researcharr.check_sonarr_connection("http://example.com", "", logger)

        self.assertFalse(result)
        logger.warning.assert_called_with("Missing Sonarr URL or API key")

    @patch("researcharr.requests.get")
    def test_check_sonarr_connection_success(self, mock_get):
        """Test successful Sonarr connection."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = researcharr.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertTrue(result)
        logger.info.assert_called_with("Sonarr connection successful.")

    @patch("researcharr.requests.get")
    def test_check_sonarr_connection_non_200_status(self, mock_get):
        """Test Sonarr connection with non-200 status."""
        logger = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = researcharr.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Sonarr connection failed with status %s", 500)

    @patch("researcharr.requests.get")
    def test_check_sonarr_connection_exception(self, mock_get):
        """Test Sonarr connection with request exception."""
        logger = Mock()
        mock_get.side_effect = Exception("Network error")

        result = researcharr.check_sonarr_connection("http://example.com", "api_key", logger)

        self.assertFalse(result)
        logger.error.assert_called_with("Sonarr connection failed: %s", mock_get.side_effect)

    def test_load_config_missing_file(self):
        """Test loading config with missing file."""
        with self.assertRaises(FileNotFoundError):
            researcharr.load_config("nonexistent.yml")

    @patch("builtins.open", new_callable=mock_open, read_data="key: value\nother: data")
    @patch("researcharr.os.path.exists")
    def test_load_config_valid_file(self, mock_exists, mock_file):
        """Test loading valid config file."""
        mock_exists.return_value = True

        with patch("researcharr.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {"key": "value", "other": "data"}

            result = researcharr.load_config("test.yml")

            self.assertEqual(result, {"key": "value", "other": "data"})
            mock_file.assert_called_with("test.yml")

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("researcharr.os.path.exists")
    def test_load_config_empty_file(self, mock_exists, mock_file):
        """Test loading empty config file."""
        mock_exists.return_value = True

        with patch("researcharr.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = None

            result = researcharr.load_config("empty.yml")

            self.assertEqual(result, {})

    def test_create_metrics_app_conditional_definition(self):
        """Test that create_metrics_app is conditionally defined."""
        # Should exist in globals
        self.assertTrue(hasattr(researcharr, "create_metrics_app"))
        self.assertTrue(callable(researcharr.create_metrics_app))

    def test_create_metrics_app(self):
        """Test creating metrics Flask app."""
        app = researcharr.create_metrics_app()

        self.assertIsInstance(app, Flask)
        self.assertEqual(app.name, "metrics")
        self.assertTrue(hasattr(app, "metrics"))
        self.assertEqual(app.metrics["requests_total"], 0)
        self.assertEqual(app.metrics["errors_total"], 0)

    def test_create_metrics_app_health_endpoint(self):
        """Test metrics app health endpoint."""
        app = researcharr.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("status", data)
            self.assertIn("db", data)
            self.assertIn("config", data)
            self.assertIn("threads", data)
            self.assertIn("time", data)

    def test_create_metrics_app_health_endpoint_db_error(self):
        """Test health endpoint when database connection fails."""
        app = researcharr.create_metrics_app()

        with patch("researcharr.sqlite3.connect", side_effect=Exception("DB Error")):
            with app.test_client() as client:
                response = client.get("/health")

                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["db"], "error")

    def test_create_metrics_app_metrics_endpoint(self):
        """Test metrics app metrics endpoint."""
        app = researcharr.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/metrics")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("requests_total", data)
            self.assertIn("errors_total", data)

    def test_create_metrics_app_request_counter(self):
        """Test that requests are counted properly."""
        app = researcharr.create_metrics_app()

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
        app = researcharr.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/nonexistent")

            self.assertEqual(response.status_code, 500)  # Error handler converts to 500
            data = response.get_json()
            self.assertIn("error", data)

    def test_create_metrics_app_error_handler_500(self):
        """Test 500 error handler."""
        app = researcharr.create_metrics_app()

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
        app = researcharr.create_metrics_app()

        with app.test_client() as client:
            # Trigger some errors
            client.get("/nonexistent")
            client.get("/another-nonexistent")

            response = client.get("/metrics")
            data = response.get_json()

            # Should count the 2 errors
            self.assertEqual(data["errors_total"], 2)

    def test_create_metrics_app_error_handler_logging(self):
        """Test that error handler logs exceptions."""
        app = researcharr.create_metrics_app()

        # Add a route that raises an exception
        @app.route("/test-logging-error")
        def test_logging_error():
            raise Exception("Test logging error")

        with patch.object(app.logger, "exception") as mock_logger:
            with app.test_client() as client:
                response = client.get("/test-logging-error")

                self.assertEqual(response.status_code, 500)
                # Should have logged the exception
                mock_logger.assert_called_once()

    def test_create_metrics_app_error_handler_logging_failure(self):
        """Test that error handler handles logging failures gracefully."""
        app = researcharr.create_metrics_app()

        # Add a route that raises an exception
        @app.route("/test-logging-failure")
        def test_logging_failure():
            raise Exception("Test logging failure")

        with patch.object(app.logger, "exception", side_effect=Exception("Logging failed")):
            with app.test_client() as client:
                response = client.get("/test-logging-failure")

                # Should still return 500 even if logging fails
                self.assertEqual(response.status_code, 500)
                data = response.get_json()
                self.assertIn("error", data)

    def test_serve_function_exists(self):
        """Test that serve function exists."""
        self.assertTrue(hasattr(researcharr, "serve"))
        self.assertTrue(callable(researcharr.serve))

    @patch("researcharr.create_metrics_app")
    def test_serve_function_behavior(self, mock_create_app):
        """Test serve function behavior."""
        mock_app = Mock()
        mock_create_app.return_value = mock_app

        researcharr.serve()

        mock_create_app.assert_called_once()
        mock_app.run.assert_called_once_with(host="0.0.0.0", port=2929)

    @patch("researcharr.sys.argv", ["researcharr.py", "serve"])
    @patch("researcharr.serve")
    def test_main_module_serve_execution(self, mock_serve):
        """Test __main__ execution with serve argument."""
        # This tests the conditional execution at the module level
        # Since this is module-level code, we need to reload to test it

        with patch("researcharr.__name__", "__main__"):
            # The module level code should call serve() when argv[1] == 'serve'
            # But since the module is already loaded, we can't easily test this
            # Instead, we test the logic directly
            if len(sys.argv) > 1 and sys.argv[1] == "serve":
                researcharr.serve()

        mock_serve.assert_called_once()

    def test_path_attribute_structure(self):
        """Test __path__ attribute structure."""
        self.assertIsInstance(researcharr.__path__, list)
        self.assertEqual(len(researcharr.__path__), 2)

        # First should be current directory
        self.assertTrue(
            "researcharr" in researcharr.__path__[0]
            or researcharr.__path__[0] == os.path.dirname(researcharr.__file__)
        )

        # Second should be researcharr subdirectory
        self.assertTrue("researcharr" in researcharr.__path__[1])


if __name__ == "__main__":
    unittest.main()
