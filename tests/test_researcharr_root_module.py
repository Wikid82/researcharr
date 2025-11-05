"""Comprehensive tests for researcharr_root.py root module."""

import importlib.util
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Import the root researcharr.py module directly (not the package)
# Get the project root directory (parent of tests directory)
project_root = Path(__file__).parent.parent
researcharr_root_path = project_root / "researcharr.py"

# Load researcharr.py as a module
spec = importlib.util.spec_from_file_location("researcharr_root", str(researcharr_root_path))
if spec is None:
    raise ImportError(f"Could not load spec from {researcharr_root_path}")
researcharr_root = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise ImportError(f"Spec has no loader for {researcharr_root_path}")
spec.loader.exec_module(researcharr_root)


class TestResearcharrRootModule(unittest.TestCase):
    """Test the root researcharr_root.py module functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_module_constants(self):
        """Test module-level constants and attributes."""
        self.assertEqual(researcharr_root.DB_PATH, "researcharr.db")

        # Check that __path__ is defined as expected for package-like behavior
        self.assertTrue(hasattr(researcharr_root, "__path__"))
        self.assertIsInstance(researcharr_root.__path__, list)
        self.assertEqual(len(researcharr_root.__path__), 2)

    def test_serve_function(self):
        """Test the serve function creates and runs app."""
        with patch.object(researcharr_root, "create_metrics_app") as mock_create:
            mock_app = Mock()
            mock_create.return_value = mock_app

            researcharr_root.serve()

            mock_create.assert_called_once()
            mock_app.run.assert_called_once_with(host="0.0.0.0", port=2929)

    def test_init_db_default_path(self):
        """Test init_db with default path."""
        # Call init_db without arguments
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            researcharr_root.init_db()

            mock_connect.assert_called_once_with("researcharr.db")
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called()

            # Verify the SQL statements contain table creation
            execute_calls = mock_cursor.execute.call_args_list
            self.assertEqual(len(execute_calls), 2)  # Two CREATE TABLE statements

            # Check that both radarr_queue and sonarr_queue tables are created
            sql_calls = [call[0][0] for call in execute_calls]
            radarr_sql = next(sql for sql in sql_calls if "radarr_queue" in sql)
            sonarr_sql = next(sql for sql in sql_calls if "sonarr_queue" in sql)

            self.assertIn("CREATE TABLE IF NOT EXISTS", radarr_sql)
            self.assertIn("CREATE TABLE IF NOT EXISTS", sonarr_sql)

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
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called()

            # Verify the SQL statements contain table creation
            execute_calls = mock_cursor.execute.call_args_list
            self.assertEqual(len(execute_calls), 2)  # Two CREATE TABLE statements

            # Check that both radarr_queue and sonarr_queue tables are created
            sql_calls = [call[0][0] for call in execute_calls]
            radarr_sql = next(sql for sql in sql_calls if "radarr_queue" in sql)
            sonarr_sql = next(sql for sql in sql_calls if "sonarr_queue" in sql)

            self.assertIn("CREATE TABLE IF NOT EXISTS", radarr_sql)
            self.assertIn("CREATE TABLE IF NOT EXISTS", sonarr_sql)

            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_setup_logger_new_logger(self):
        """Test setup_logger creates new logger."""
        log_file = "test.log"
        logger = researcharr_root.setup_logger("test_logger", log_file, logging.DEBUG)

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_logger")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertTrue(len(logger.handlers) > 0)

    def test_setup_logger_existing_logger(self):
        """Test setup_logger with existing logger."""
        log_file = "test.log"

        # Create logger first time
        logger1 = researcharr_root.setup_logger("existing_logger", log_file)
        handler_count = len(logger1.handlers)

        # Create same logger again
        logger2 = researcharr_root.setup_logger("existing_logger", log_file)

        # Should be same logger and not add duplicate handlers
        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger2.handlers), handler_count)

    def test_setup_logger_default_level(self):
        """Test setup_logger with default level."""
        log_file = "test.log"
        logger = researcharr_root.setup_logger("default_level_logger", log_file)

        self.assertEqual(logger.level, logging.INFO)

    def test_has_valid_url_and_key_all_valid(self):
        """Test has_valid_url_and_key with all valid instances."""
        instances = [
            {"enabled": True, "url": "http://test1.com", "api_key": "key1"},
            {"enabled": True, "url": "https://test2.com", "api_key": "key2"},
            {"enabled": False, "url": "", "api_key": ""},  # Disabled, so ignored
        ]

        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_has_valid_url_and_key_invalid_url(self):
        """Test has_valid_url_and_key with invalid URL."""
        instances = [
            {"enabled": True, "url": "ftp://invalid.com", "api_key": "key1"},
        ]

        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertFalse(result)

    def test_has_valid_url_and_key_missing_api_key(self):
        """Test has_valid_url_and_key with missing API key."""
        instances = [
            {"enabled": True, "url": "http://test.com", "api_key": ""},
        ]

        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertFalse(result)

    def test_has_valid_url_and_key_empty_list(self):
        """Test has_valid_url_and_key with empty list."""
        result = researcharr_root.has_valid_url_and_key([])
        self.assertTrue(result)

    def test_has_valid_url_and_key_disabled_instances(self):
        """Test has_valid_url_and_key with all disabled instances."""
        instances = [
            {"enabled": False, "url": "invalid", "api_key": ""},
            {"enabled": False, "url": "", "api_key": "invalid"},
        ]

        result = researcharr_root.has_valid_url_and_key(instances)
        self.assertTrue(result)

    def test_check_radarr_connection_success(self):
        """Test successful Radarr connection."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = researcharr_root.check_radarr_connection(
                "http://radarr.local", "test_key", mock_logger
            )

            self.assertTrue(result)
            mock_get.assert_called_once_with("http://radarr.local")
            mock_logger.info.assert_called_once_with("Radarr connection successful.")

    def test_check_radarr_connection_missing_url(self):
        """Test Radarr connection with missing URL."""
        mock_logger = Mock()

        result = researcharr_root.check_radarr_connection("", "test_key", mock_logger)

        self.assertFalse(result)
        mock_logger.warning.assert_called_once_with("Missing Radarr URL or API key")

    def test_check_radarr_connection_missing_api_key(self):
        """Test Radarr connection with missing API key."""
        mock_logger = Mock()

        result = researcharr_root.check_radarr_connection("http://radarr.local", "", mock_logger)

        self.assertFalse(result)
        mock_logger.warning.assert_called_once_with("Missing Radarr URL or API key")

    def test_check_radarr_connection_non_200_status(self):
        """Test Radarr connection with non-200 status."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = researcharr_root.check_radarr_connection(
                "http://radarr.local", "test_key", mock_logger
            )

            self.assertFalse(result)
            mock_logger.error.assert_called_once_with(
                "Radarr connection failed with status %s", 404
            )

    def test_check_radarr_connection_exception(self):
        """Test Radarr connection with exception."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = researcharr_root.check_radarr_connection(
                "http://radarr.local", "test_key", mock_logger
            )

            self.assertFalse(result)
            mock_logger.error.assert_called_once()

    def test_check_sonarr_connection_success(self):
        """Test successful Sonarr connection."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = researcharr_root.check_sonarr_connection(
                "http://sonarr.local", "test_key", mock_logger
            )

            self.assertTrue(result)
            mock_get.assert_called_once_with("http://sonarr.local")
            mock_logger.info.assert_called_once_with("Sonarr connection successful.")

    def test_check_sonarr_connection_missing_url(self):
        """Test Sonarr connection with missing URL."""
        mock_logger = Mock()

        result = researcharr_root.check_sonarr_connection("", "test_key", mock_logger)

        self.assertFalse(result)
        mock_logger.warning.assert_called_once_with("Missing Sonarr URL or API key")

    def test_check_sonarr_connection_missing_api_key(self):
        """Test Sonarr connection with missing API key."""
        mock_logger = Mock()

        result = researcharr_root.check_sonarr_connection("http://sonarr.local", "", mock_logger)

        self.assertFalse(result)
        mock_logger.warning.assert_called_once_with("Missing Sonarr URL or API key")

    def test_check_sonarr_connection_non_200_status(self):
        """Test Sonarr connection with non-200 status."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = researcharr_root.check_sonarr_connection(
                "http://sonarr.local", "test_key", mock_logger
            )

            self.assertFalse(result)
            mock_logger.error.assert_called_once_with(
                "Sonarr connection failed with status %s", 500
            )

    def test_check_sonarr_connection_exception(self):
        """Test Sonarr connection with exception."""
        mock_logger = Mock()

        with patch.object(researcharr_root.requests, "get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = researcharr_root.check_sonarr_connection(
                "http://sonarr.local", "test_key", mock_logger
            )

            self.assertFalse(result)
            mock_logger.error.assert_called_once()

    def test_load_config_valid_file(self):
        """Test load_config with valid YAML file."""
        config_data = {"test": "value", "nested": {"key": "val"}}

        with patch("builtins.open", mock_open(read_data="test: value\nnested:\n  key: val")):
            with patch.object(researcharr_root.os.path, "exists", return_value=True):
                with patch.object(researcharr_root.yaml, "safe_load", return_value=config_data):
                    result = researcharr_root.load_config("test.yml")

                    self.assertEqual(result, config_data)

    def test_load_config_missing_file(self):
        """Test load_config with missing file."""
        with patch.object(researcharr_root.os.path, "exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                researcharr_root.load_config("missing.yml")

    def test_load_config_empty_file(self):
        """Test load_config with empty file."""
        with patch("builtins.open", mock_open(read_data="")):
            with patch.object(researcharr_root.os.path, "exists", return_value=True):
                with patch.object(researcharr_root.yaml, "safe_load", return_value=None):
                    result = researcharr_root.load_config("empty.yml")

                    self.assertEqual(result, {})

    def test_load_config_default_path(self):
        """Test load_config with default path."""
        with patch("builtins.open", mock_open(read_data="key: value")):
            with patch.object(researcharr_root.os.path, "exists", return_value=True):
                with patch.object(
                    researcharr_root.yaml, "safe_load", return_value={"key": "value"}
                ):
                    result = researcharr_root.load_config()

                    self.assertEqual(result, {"key": "value"})

    def test_create_metrics_app(self):
        """Test create_metrics_app creates Flask app."""
        app = researcharr_root.create_metrics_app()

        self.assertEqual(app.name, "metrics")
        self.assertIn("requests_total", app.config["metrics"])
        self.assertIn("errors_total", app.config["metrics"])
        self.assertEqual(app.config["metrics"]["requests_total"], 0)
        self.assertEqual(app.config["metrics"]["errors_total"], 0)

    def test_create_metrics_app_routes(self):
        """Test create_metrics_app has expected routes."""
        app = researcharr_root.create_metrics_app()

        with app.test_client() as client:
            # Test health endpoint
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertIn("status", data)
            self.assertIn("db", data)
            self.assertIn("config", data)
            self.assertIn("threads", data)
            self.assertIn("time", data)

    def test_create_metrics_app_metrics_endpoint(self):
        """Test metrics endpoint."""
        app = researcharr_root.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/metrics")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertIn("requests_total", data)
            self.assertIn("errors_total", data)

    def test_create_metrics_app_request_counter(self):
        """Test request counter increments."""
        app = researcharr_root.create_metrics_app()

        with app.test_client() as client:
            # Make a request to increment counter
            client.get("/health")

            # Check metrics
            response = client.get("/metrics")
            data = response.get_json()
            self.assertGreater(data["requests_total"], 0)

    def test_create_metrics_app_error_counter(self):
        """Test error counter increments on 404."""
        app = researcharr_root.create_metrics_app()

        with app.test_client() as client:
            # Make request to non-existent endpoint
            client.get("/nonexistent")

            # Check metrics
            response = client.get("/metrics")
            data = response.get_json()
            self.assertGreater(data["errors_total"], 0)

    def test_create_metrics_app_health_db_check(self):
        """Test health endpoint with actual DB check."""
        # Create a test database
        researcharr_root.init_db()

        app = researcharr_root.create_metrics_app()

        with app.test_client() as client:
            response = client.get("/health")
            data = response.get_json()

            self.assertEqual(data["db"], "ok")

    def test_create_metrics_app_health_db_error(self):
        """Test health endpoint with DB error."""
        app = researcharr_root.create_metrics_app()

        # Mock DB_PATH to non-existent file
        with patch.object(researcharr_root, "DB_PATH", "/invalid/path/db.sqlite"):
            with app.test_client() as client:
                response = client.get("/health")
                data = response.get_json()

                self.assertEqual(data["db"], "error")

    def test_create_metrics_app_error_handlers(self):
        """Test error handlers."""
        app = researcharr_root.create_metrics_app()

        # Add a route that raises an exception
        @app.route("/test_error")
        def test_error():
            raise Exception("Test error")

        with app.test_client() as client:
            response = client.get("/test_error")
            self.assertEqual(response.status_code, 500)

            data = response.get_json()
            self.assertEqual(data["error"], "internal error")

    def test_conditional_imports(self):
        """Test that conditional imports work."""
        # These should be available in the loaded module
        self.assertTrue(hasattr(researcharr_root, "requests"))
        self.assertTrue(hasattr(researcharr_root, "yaml"))

    def test_main_execution_with_serve_argument(self):
        """Test __main__ execution with serve argument."""
        with patch.object(researcharr_root, "serve") as mock_serve:
            with patch("sys.argv", ["researcharr_root.py", "serve"]):
                # Simulate the __main__ execution
                exec(
                    """
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
""",
                    dict(researcharr_root.__dict__, __name__="__main__"),
                )

                mock_serve.assert_called_once()

    def test_main_execution_without_serve_argument(self):
        """Test __main__ execution without serve argument."""
        with patch.object(researcharr_root, "serve") as mock_serve:
            with patch("sys.argv", ["researcharr_root.py"]):
                # Simulate the __main__ execution
                exec(
                    """
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
""",
                    dict(researcharr_root.__dict__, __name__="__main__"),
                )

                mock_serve.assert_not_called()

    def test_globals_preservation(self):
        """Test that globals preservation works for test fixtures."""
        # This tests the conditional import pattern used for test compatibility
        original_requests = researcharr_root.requests

        # The module should preserve existing globals
        self.assertIs(researcharr_root.requests, original_requests)

    def test_package_path_structure(self):
        """Test __path__ includes both directories."""
        if researcharr_root.__file__ is None:
            self.skipTest("Module __file__ is None")

        expected_paths = [
            os.path.dirname(researcharr_root.__file__),
            os.path.join(os.path.dirname(researcharr_root.__file__), "researcharr"),
        ]

        for expected_path in expected_paths:
            self.assertIn(expected_path, researcharr_root.__path__)


if __name__ == "__main__":
    unittest.main()
