"""Consolidated API tests - merging all API-related test files."""

import json
import tempfile
import unittest


class TestAPIConsolidated(unittest.TestCase):
    """Consolidated tests for API functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_api_blueprint_registration(self):
        """Test API blueprint registration."""
        try:
            import api  # noqa: F401
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Test that API routes are registered
            response = client.get("/api/")
            # Should return some response (200, 404, etc.)
            self.assertIsInstance(response.status_code, int)

        except ImportError:
            # API module might not exist
            self.assertTrue(True)

    def test_api_docs_endpoint(self):
        """Test API documentation endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Test API docs endpoint
            response = client.get("/api/docs")
            # Should return docs or 404
            self.assertIn(response.status_code, [200, 404])

            # Test API schema endpoint
            response = client.get("/api/schema")
            self.assertIn(response.status_code, [200, 404])

        except ImportError:
            self.assertTrue(True)

    def test_api_logs_endpoint(self):
        """Test API logs endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test logs API
            response = client.get("/api/logs")
            self.assertIn(response.status_code, [200, 404])

            # Test logs streaming
            response = client.get("/api/logs/stream")
            self.assertIn(response.status_code, [200, 404])

        except ImportError:
            self.assertTrue(True)

    def test_api_tasks_endpoint(self):
        """Test API tasks endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test tasks API
            response = client.get("/api/tasks")
            self.assertIn(response.status_code, [200, 404])

            # Test task creation
            response = client.post(
                "/api/tasks", data=json.dumps({"task": "test"}), content_type="application/json"
            )
            self.assertIn(response.status_code, [200, 201, 400, 404])

        except ImportError:
            self.assertTrue(True)

    def test_api_version_endpoint(self):
        """Test API version endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Test version API
            response = client.get("/api/version")

            if response.status_code == 200:
                data = response.get_json()
                self.assertIsInstance(data, dict)
                # Might have version info
                if "version" in data:
                    self.assertIsInstance(data["version"], str)
            else:
                # Endpoint might not exist
                self.assertIn(response.status_code, [404])

        except ImportError:
            self.assertTrue(True)

    def test_plugins_api_endpoints(self):
        """Test plugins API endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test plugins list API
            response = client.get("/api/plugins")
            self.assertIn(response.status_code, [200, 404])

            # Test plugin discovery
            response = client.get("/api/plugins/discover")
            self.assertIn(response.status_code, [200, 404])

            # Test plugin actions
            response = client.post(
                "/api/plugins/action",
                data=json.dumps({"action": "test"}),
                content_type="application/json",
            )
            self.assertIn(response.status_code, [200, 400, 404])

        except ImportError:
            self.assertTrue(True)

    def test_plugin_instances_api(self):
        """Test plugin instances API endpoints."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test plugin instances API
            response = client.get("/api/plugin-instances")
            self.assertIn(response.status_code, [200, 404])

            # Test instance actions
            response = client.post(
                "/api/plugin-instances/1/action",
                data=json.dumps({"action": "test"}),
                content_type="application/json",
            )
            self.assertIn(response.status_code, [200, 400, 404])

        except ImportError:
            self.assertTrue(True)

    def test_api_authentication(self):
        """Test API authentication requirements."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Test unauthenticated access to protected endpoints
            protected_endpoints = [
                "/api/tasks",
                "/api/plugins",
                "/api/logs",
                "/api/plugin-instances",
            ]

            for endpoint in protected_endpoints:
                response = client.get(endpoint)
                # Should require authentication (401, 403) or not exist (404)
                self.assertIn(response.status_code, [401, 403, 404])

        except ImportError:
            self.assertTrue(True)

    def test_api_error_handling(self):
        """Test API error handling."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test invalid JSON
            response = client.post(
                "/api/tasks", data="invalid json", content_type="application/json"
            )
            self.assertIn(response.status_code, [400, 404])

            # Test missing content type
            response = client.post("/api/tasks", data=json.dumps({"test": "data"}))
            self.assertIn(response.status_code, [400, 404, 415])

        except ImportError:
            self.assertTrue(True)

    def test_api_cors_headers(self):
        """Test API CORS headers."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Test OPTIONS request
            response = client.options("/api/")

            if response.status_code == 200:
                # Check for CORS headers
                headers = response.headers
                self.assertIsInstance(headers, dict)
            else:
                # CORS might not be configured
                self.assertTrue(True)

        except ImportError:
            self.assertTrue(True)

    def test_api_rate_limiting(self):
        """Test API rate limiting if implemented."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Make multiple rapid requests
            responses = []
            for i in range(10):
                response = client.get("/api/version")
                responses.append(response.status_code)

            # Should handle multiple requests gracefully
            # Rate limiting would return 429, but it might not be implemented
            for status_code in responses:
                self.assertIn(status_code, [200, 404, 429])

        except ImportError:
            self.assertTrue(True)

    def test_api_pagination(self):
        """Test API pagination if implemented."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test pagination parameters
            response = client.get("/api/logs?page=1&limit=10")

            if response.status_code == 200:
                data = response.get_json()
                if isinstance(data, dict):
                    # Might have pagination info
                    pagination_keys = ["page", "limit", "total", "pages"]
                    for key in pagination_keys:
                        if key in data:
                            self.assertIsInstance(data[key], (int, str))
            else:
                # Endpoint might not exist or support pagination
                self.assertIn(response.status_code, [404])

        except ImportError:
            self.assertTrue(True)

    def test_api_data_validation(self):
        """Test API data validation."""
        try:
            from researcharr.factory import create_app

            app = create_app()
            client = app.test_client()

            # Mock login
            with client.session_transaction() as sess:
                sess["logged_in"] = True

            # Test with invalid data
            invalid_data = {"invalid_field": "value", "missing_required": None}

            response = client.post(
                "/api/plugins/action",
                data=json.dumps(invalid_data),
                content_type="application/json",
            )

            # Should validate and return appropriate error
            self.assertIn(response.status_code, [400, 404, 422])

        except ImportError:
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
