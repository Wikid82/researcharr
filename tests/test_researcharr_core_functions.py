"""Test module for researcharr.researcharr core functions."""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestResearcharrResearcharrModule:
    """Test cases for the researcharr.researcharr module."""

    def test_module_import(self):
        """Test that researcharr.researcharr module imports correctly."""
        import researcharr

        assert researcharr.researcharr is not None
        assert hasattr(researcharr.researcharr, "init_db")
        assert hasattr(researcharr.researcharr, "create_metrics_app")

    def test_init_db_default_path(self):
        """Test database initialization with default path."""
        import researcharr

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                researcharr.researcharr.init_db()

                # Verify database file was created
                assert os.path.exists("researcharr.db")

                # Verify tables were created
                conn = sqlite3.connect("researcharr.db")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                assert "radarr_queue" in tables
                assert "sonarr_queue" in tables
                conn.close()

                # Clean up
                os.remove("researcharr.db")
            finally:
                os.chdir(old_cwd)

    def test_init_db_custom_path(self):
        """Test database initialization with custom path."""
        import researcharr

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmpfile:
            custom_path = tmpfile.name

        try:
            researcharr.researcharr.init_db(custom_path)

            # Verify database file exists
            assert os.path.exists(custom_path)

            # Verify tables were created
            conn = sqlite3.connect(custom_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "radarr_queue" in tables
            assert "sonarr_queue" in tables
            conn.close()
        finally:
            if os.path.exists(custom_path):
                os.remove(custom_path)

    def test_create_metrics_app(self):
        """Test that create_metrics_app returns a Flask app."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()
        assert app is not None
        assert hasattr(app, "run")
        assert hasattr(app, "test_client")

    def test_create_metrics_app_health_endpoint(self):
        """Test that metrics app has health endpoint."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()
        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert "db" in data

    def test_create_metrics_app_metrics_endpoint(self):
        """Test that metrics app has metrics endpoint."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()
        with app.test_client() as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            data = response.get_json()
            assert "requests_total" in data
            assert "errors_total" in data

    def test_setup_logger(self):
        """Test setup_logger creates a logger."""
        import researcharr

        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmpfile:
            log_file = tmpfile.name

        try:
            logger = researcharr.researcharr.setup_logger("test_logger", log_file)
            assert logger is not None
            assert hasattr(logger, "info")
            assert logger.name == "test_logger"
        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    def test_has_valid_url_and_key(self):
        """Test has_valid_url_and_key function."""
        import researcharr

        # Test with valid instances
        valid_instances = [
            {"enabled": True, "url": "http://example.com", "api_key": "valid_key"},
            {"enabled": False, "url": "", "api_key": ""},
        ]
        assert researcharr.researcharr.has_valid_url_and_key(valid_instances) is True

        # Test with invalid instances
        invalid_instances = [
            {"enabled": True, "url": "invalid_url", "api_key": "key"},
        ]
        assert researcharr.researcharr.has_valid_url_and_key(invalid_instances) is False

    def test_check_radarr_connection_missing_params(self):
        """Test radarr connection check with missing parameters."""
        import researcharr

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_radarr_connection("", "", mock_logger)
        assert result is False
        mock_logger.warning.assert_called()

    @patch("researcharr.researcharr.requests")
    def test_check_radarr_connection_success(self, mock_requests):
        """Test successful radarr connection."""
        import researcharr

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_radarr_connection(
            "http://localhost:7878", "test_key", mock_logger
        )
        assert result is True

    @patch("researcharr.researcharr.requests")
    def test_check_radarr_connection_error(self, mock_requests):
        """Test radarr connection with error."""
        import researcharr

        mock_requests.get.side_effect = Exception("Connection failed")

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_radarr_connection(
            "http://localhost:7878", "test_key", mock_logger
        )
        assert result is False

    def test_check_sonarr_connection_missing_params(self):
        """Test sonarr connection check with missing parameters."""
        import researcharr

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_sonarr_connection("", "", mock_logger)
        assert result is False
        mock_logger.warning.assert_called()

    @patch("researcharr.researcharr.requests")
    def test_check_sonarr_connection_success(self, mock_requests):
        """Test successful sonarr connection."""
        import researcharr

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_sonarr_connection(
            "http://localhost:8989", "test_key", mock_logger
        )
        assert result is True

    @patch("researcharr.researcharr.requests")
    def test_check_sonarr_connection_error(self, mock_requests):
        """Test sonarr connection with error."""
        import researcharr

        mock_requests.get.side_effect = Exception("Connection failed")

        mock_logger = MagicMock()
        result = researcharr.researcharr.check_sonarr_connection(
            "http://localhost:8989", "test_key", mock_logger
        )
        assert result is False

    def test_load_config_valid_file(self):
        """Test loading valid config file."""
        import researcharr

        config_data = {"test": "value", "number": 42}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmpfile:
            import yaml

            yaml.dump(config_data, tmpfile)
            config_file = tmpfile.name

        try:
            config = researcharr.researcharr.load_config(config_file)
            assert config == config_data
        finally:
            os.remove(config_file)

    def test_load_config_missing_file(self):
        """Test loading non-existent config file."""
        import researcharr

        with pytest.raises(FileNotFoundError):
            researcharr.researcharr.load_config("/nonexistent/config.yml")

    def test_load_config_empty_file(self):
        """Test loading empty config file."""
        import researcharr

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmpfile:
            tmpfile.write("")
            config_file = tmpfile.name

        try:
            config = researcharr.researcharr.load_config(config_file)
            assert config == {}
        finally:
            os.remove(config_file)

    def test_serve_function_exists(self):
        """Test that serve function exists."""
        import researcharr

        # Test that the function exists and is callable
        assert hasattr(researcharr.researcharr, "serve")
        assert callable(researcharr.researcharr.serve)

    @patch("researcharr.researcharr.create_metrics_app")
    def test_serve_function_behavior(self, mock_create_app):
        """Test that serve function creates and runs the app correctly."""
        import researcharr

        # Mock the Flask app
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        # Call serve function
        researcharr.researcharr.serve()

        # Verify the app was created and run with correct parameters
        mock_create_app.assert_called_once()
        mock_app.run.assert_called_once_with(host="0.0.0.0", port=2929)

    def test_error_handler_endpoints(self):
        """Test that the metrics app has error handlers."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()
        with app.test_client() as client:
            # Test 404 handler - actually returns 500 because of how error handler is written
            response = client.get("/nonexistent")
            assert response.status_code == 500  # Error handler always returns 500

            # Check that error count was incremented
            metrics_response = client.get("/metrics")
            data = metrics_response.get_json()
            assert data["errors_total"] > 0

    def test_app_has_metrics_tracking(self):
        """Test that the app tracks metrics correctly."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()
        with app.test_client() as client:
            # Make several requests
            client.get("/health")
            client.get("/health")
            client.get("/metrics")

            # Check metrics
            response = client.get("/metrics")
            data = response.get_json()
            assert data["requests_total"] >= 3

    def test_db_path_constant(self):
        """Test that DB_PATH constant is available."""
        import researcharr

        assert hasattr(researcharr.researcharr, "DB_PATH")
        assert researcharr.researcharr.DB_PATH == "researcharr.db"

    def test_conditional_imports_exist(self):
        """Test that conditional imports are available."""
        import researcharr

        # These should be available after import
        assert hasattr(researcharr.researcharr, "requests")
        assert hasattr(researcharr.researcharr, "yaml")

    def test_logger_with_level(self):
        """Test setup_logger with specific level."""
        import logging

        import researcharr

        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmpfile:
            log_file = tmpfile.name

        try:
            logger = researcharr.researcharr.setup_logger(
                "test_logger_level", log_file, logging.DEBUG
            )
            assert logger.level == logging.DEBUG
        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    def test_app_error_increment(self):
        """Test that error handlers increment error count."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()

        # Get initial metrics
        with app.test_client() as client:
            response = client.get("/metrics")
            initial_errors = response.get_json()["errors_total"]

            # Trigger 404 error
            client.get("/nonexistent")

            # Check that error count increased
            response = client.get("/metrics")
            new_errors = response.get_json()["errors_total"]
            assert new_errors > initial_errors

    def test_health_endpoint_db_check(self):
        """Test that health endpoint checks database."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Initialize a test DB
                researcharr.researcharr.init_db()

                with app.test_client() as client:
                    response = client.get("/health")
                    data = response.get_json()

                    assert data["status"] == "ok"
                    assert data["db"] == "ok"
            finally:
                os.chdir(old_cwd)

    def test_missing_imports_handling(self):
        """Test behavior when optional imports are missing."""
        import researcharr

        # Test requests=None scenario
        original_requests = researcharr.researcharr.requests
        try:
            researcharr.researcharr.requests = None

            mock_logger = MagicMock()
            result = researcharr.researcharr.check_radarr_connection(
                "http://test.com", "key", mock_logger
            )
            assert result is False
            mock_logger.warning.assert_called_with("requests not available in this environment")

            result = researcharr.researcharr.check_sonarr_connection(
                "http://test.com", "key", mock_logger
            )
            assert result is False
        finally:
            researcharr.researcharr.requests = original_requests

    def test_yaml_none_handling(self):
        """Test behavior when yaml import is None."""
        import researcharr

        original_yaml = researcharr.researcharr.yaml
        try:
            researcharr.researcharr.yaml = None

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmpfile:
                tmpfile.write("test: value")
                config_file = tmpfile.name

            try:
                config = researcharr.researcharr.load_config(config_file)
                assert config == {}  # Should return empty dict when yaml is None
            finally:
                os.remove(config_file)
        finally:
            researcharr.researcharr.yaml = original_yaml

    def test_connection_non_200_status(self):
        """Test connection functions with non-200 status codes."""
        import researcharr

        with patch("researcharr.researcharr.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_requests.get.return_value = mock_response

            mock_logger = MagicMock()

            # Test Radarr with 404
            result = researcharr.researcharr.check_radarr_connection(
                "http://localhost:7878", "key", mock_logger
            )
            assert result is False
            mock_logger.error.assert_called_with("Radarr connection failed with status %s", 404)

            # Test Sonarr with 404
            result = researcharr.researcharr.check_sonarr_connection(
                "http://localhost:8989", "key", mock_logger
            )
            assert result is False
            mock_logger.error.assert_called_with("Sonarr connection failed with status %s", 404)

    def test_health_endpoint_db_error(self):
        """Test health endpoint when database connection fails."""
        import researcharr

        app = researcharr.researcharr.create_metrics_app()

        # Test with invalid DB path
        original_db_path = researcharr.researcharr.DB_PATH
        try:
            researcharr.researcharr.DB_PATH = "/invalid/path/db.sqlite"

            with app.test_client() as client:
                response = client.get("/health")
                data = response.get_json()

                assert data["status"] == "ok"
                assert data["db"] == "error"  # Should be error due to invalid path
        finally:
            researcharr.researcharr.DB_PATH = original_db_path
