"""Comprehensive tests for researcharr.core.api module.

This module tests the core API blueprint, decorators, and endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from flask import Flask


@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_secret"

    # Register the API blueprint
    from researcharr.core.api import bp

    app.register_blueprint(bp, url_prefix="/api")

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_api_blueprint_exists():
    """Test that API blueprint can be imported."""
    from researcharr.core import api

    assert hasattr(api, "bp")
    assert api.bp.name == "api_v1"  # type: ignore[attr-defined]


def test_require_api_key_decorator():
    """Test require_api_key decorator."""
    from researcharr.core.api import require_api_key

    @require_api_key
    def test_func():
        return "success"

    assert callable(test_func)


def test_require_api_key_only_decorator():
    """Test require_api_key_only decorator."""
    from researcharr.core.api import require_api_key_only

    @require_api_key_only
    def test_func():
        return "success"

    assert callable(test_func)


def test_health_endpoint(client):
    """Test health check endpoint."""
    with patch("researcharr.core.api.get_container") as mock_container:
        mock_health_service = MagicMock()
        mock_health_service.check_system_health.return_value = {
            "status": "ok",
            "components": {"database": {"status": "ok"}, "configuration": {"status": "ok"}},
        }

        mock_cont = MagicMock()
        mock_cont.resolve.return_value = mock_health_service
        mock_container.return_value = mock_cont

        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


def test_health_endpoint_error():
    """Test health endpoint handles errors."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from researcharr.core.api import bp

    app.register_blueprint(bp, url_prefix="/api")

    client = app.test_client()

    with patch("researcharr.core.api.get_container", side_effect=Exception("Container error")):
        response = client.get("/api/health")

        # Should return error response
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data


def test_health_endpoint_fallback():
    """Test health endpoint fallback."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from researcharr.core.api import bp

    app.register_blueprint(bp, url_prefix="/api")

    client = app.test_client()

    # Mock container to raise on resolve
    with patch("researcharr.core.api.get_container") as mock_container:
        mock_cont = MagicMock()
        mock_cont.resolve.side_effect = Exception("Service error")
        mock_container.return_value = mock_cont

        response = client.get("/api/health")

        assert response.status_code in (200, 503)


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    with patch("researcharr.core.api.get_container") as mock_container:
        mock_metrics_service = MagicMock()
        mock_metrics_service.get_metrics.return_value = {"requests": 100}

        mock_cont = MagicMock()
        mock_cont.resolve.return_value = mock_metrics_service
        mock_container.return_value = mock_cont

        response = client.get("/api/metrics")

        assert response.status_code == 200
        data = response.get_json()
        assert "requests" in data


def test_metrics_endpoint_fallback(app, client):
    """Test metrics endpoint fallback."""
    app.metrics = {"fallback": True}

    with patch("researcharr.core.api.get_container", side_effect=Exception("Container error")):
        response = client.get("/api/metrics")

        assert response.status_code == 200
        data = response.get_json()
        assert data.get("fallback") is True


def test_plugins_endpoint_no_auth(client):
    """Test plugins endpoint requires authentication."""
    response = client.get("/api/plugins")

    assert response.status_code == 401


def test_plugins_endpoint_with_auth(app, client):
    """Test plugins endpoint with authentication."""
    # Set up API key
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}}

    # Mock registry
    mock_registry = MagicMock()
    mock_registry.list_plugins.return_value = ["test_plugin"]
    mock_registry.get.return_value = type(
        "TestPlugin", (), {"category": "test", "description": "Test plugin"}
    )

    app.plugin_registry = mock_registry

    with patch("researcharr.core.api.get_event_bus") as mock_bus:
        mock_bus.return_value = MagicMock()

        response = client.get("/api/plugins", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()
        assert "plugins" in data


def test_plugins_endpoint_no_registry(app, client):
    """Test plugins endpoint when no registry available."""
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}}
    app.plugin_registry = None

    with patch("researcharr.core.api.get_event_bus") as mock_bus:
        mock_bus.return_value = MagicMock()

        response = client.get("/api/plugins", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()
        assert data["plugins"] == []


def test_plugin_validate_endpoint(app, client):
    """Test plugin validation endpoint."""
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {
        "general": {"api_key_hash": api_key_hash},
        "test_plugin": [{"enabled": True}],
    }

    mock_plugin = MagicMock()
    mock_plugin.validate.return_value = True

    mock_registry = MagicMock()
    mock_registry.get.return_value = True
    mock_registry.create_instance.return_value = mock_plugin

    app.plugin_registry = mock_registry

    with patch("researcharr.core.api.get_event_bus") as mock_bus:
        mock_bus.return_value = MagicMock()

        response = client.post(
            "/api/plugins/test_plugin/validate/0", headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "result" in data


def test_plugin_validate_unknown_plugin(app, client):
    """Test validation of unknown plugin."""
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}}

    mock_registry = MagicMock()
    mock_registry.get.return_value = None

    app.plugin_registry = mock_registry

    response = client.post("/api/plugins/unknown/validate/0", headers={"X-API-Key": api_key})

    assert response.status_code == 404


def test_plugin_validate_invalid_index(app, client):
    """Test validation with invalid instance index."""
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}, "test_plugin": []}

    mock_registry = MagicMock()
    mock_registry.get.return_value = True

    app.plugin_registry = mock_registry

    response = client.post("/api/plugins/test_plugin/validate/0", headers={"X-API-Key": api_key})

    assert response.status_code == 400


def test_plugin_validate_exception(app, client):
    """Test validation handles exceptions."""
    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {
        "general": {"api_key_hash": api_key_hash},
        "test_plugin": [{"enabled": True}],
    }

    mock_registry = MagicMock()
    mock_registry.get.return_value = True
    mock_registry.create_instance.side_effect = Exception("Validation error")

    app.plugin_registry = mock_registry

    with patch("researcharr.core.api.get_event_bus") as mock_bus:
        mock_bus.return_value = MagicMock()

        response = client.post(
            "/api/plugins/test_plugin/validate/0", headers={"X-API-Key": api_key}
        )

        assert response.status_code == 500


def test_require_api_key_with_valid_key(app):
    """Test require_api_key with valid API key."""
    from researcharr.core.api import require_api_key

    @require_api_key
    def test_func():
        return {"result": "success"}

    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}}

    with app.test_request_context(headers={"X-API-Key": api_key}):
        result = test_func()
        assert result == {"result": "success"}


def test_require_api_key_with_session(app):
    """Test require_api_key with valid session."""
    from researcharr.core.api import require_api_key

    @require_api_key
    def test_func():
        return {"result": "success"}

    app.session_cookie_name = "session"

    with app.test_request_context(environ_base={"HTTP_COOKIE": "session=valid"}):
        result = test_func()
        assert result == {"result": "success"}


def test_require_api_key_unauthorized(app):
    """Test require_api_key returns 401 when unauthorized."""
    from researcharr.core.api import require_api_key

    @require_api_key
    def test_func():
        return {"result": "success"}

    with app.test_request_context():
        result, status = test_func()
        assert status == 401


def test_require_api_key_only_with_valid_key(app):
    """Test require_api_key_only with valid API key."""
    from researcharr.core.api import require_api_key_only

    @require_api_key_only
    def test_func():
        return {"result": "success"}

    api_key = "test_key"
    api_key_hash = generate_password_hash(api_key)

    app.config_data = {"general": {"api_key_hash": api_key_hash}}

    with app.test_request_context(headers={"X-API-Key": api_key}):
        result = test_func()
        assert result == {"result": "success"}


def test_require_api_key_only_no_session(app):
    """Test require_api_key_only does not accept session."""
    from researcharr.core.api import require_api_key_only

    @require_api_key_only
    def test_func():
        return {"result": "success"}

    app.session_cookie_name = "session"

    with app.test_request_context(environ_base={"HTTP_COOKIE": "session=valid"}):
        result, status = test_func()
        assert status == 401


def test_health_endpoint_503_status():
    """Test health endpoint returns 503 on unhealthy status."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from researcharr.core.api import bp

    app.register_blueprint(bp, url_prefix="/api")

    client = app.test_client()

    with patch("researcharr.core.api.get_container") as mock_container:
        mock_health_service = MagicMock()
        mock_health_service.check_system_health.return_value = {
            "status": "error",
            "components": {"database": {"status": "error"}, "configuration": {"status": "ok"}},
        }

        mock_cont = MagicMock()
        mock_cont.resolve.return_value = mock_health_service
        mock_container.return_value = mock_cont

        response = client.get("/api/health")

        assert response.status_code == 503
