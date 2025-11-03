"""Core API Module.

This module provides the core API functionality extracted from the main
api.py file, integrated with the new core architecture components.
"""

from functools import wraps

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template_string,
    request,
)
from werkzeug.security import check_password_hash

from .container import get_container
from .events import Events, get_event_bus

# Create the API blueprint
bp = Blueprint("api_v1", __name__)


def require_api_key(func):
    """Decorator that requires either valid API key or web session."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Allow either a valid session (web UI) or an API key header
        if getattr(current_app, "config_data", None) and request.headers.get("X-API-Key"):
            key = request.headers.get("X-API-Key")
            stored_hash = (
                getattr(current_app, "config_data", {}).get("general", {}).get("api_key_hash")
            )
            # If an API key hash is configured, verify the presented token
            if stored_hash and key and check_password_hash(stored_hash, key):
                return func(*args, **kwargs)

        # Fallback to web session-based auth (same as web UI)
        cookie_name = getattr(
            current_app,
            "session_cookie_name",
            current_app.config.get("SESSION_COOKIE_NAME"),
        )
        if cookie_name and request.cookies.get(cookie_name) and request.authorization is None:
            # Let the view decide if session is valid; for now allow and let
            # route-level checks mirror UI behaviour.
            return func(*args, **kwargs)

        return jsonify({"error": "unauthorized"}), 401

    return wrapper


def require_api_key_only(func):
    """Decorator that requires a valid X-API-Key header and disallows session fallback.

    Use this for endpoints that must only be accessible via a valid API token.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        stored_hash = getattr(current_app, "config_data", {}).get("general", {}).get("api_key_hash")
        if stored_hash and key and check_password_hash(stored_hash, key):
            return func(*args, **kwargs)
        return jsonify({"error": "unauthorized"}), 401

    return wrapper


@bp.route("/health")
def health():
    """Enhanced health check endpoint using core services."""
    try:
        container = get_container()
        health_service = container.resolve("health_service")
        health_status = health_service.check_system_health()

        # Maintain backwards compatibility
        db_status = health_status["components"].get("database", {}).get("status", "error")
        config_status = health_status["components"].get("configuration", {}).get("status", "ok")

        response = {
            "status": health_status["status"],
            "db": db_status,
            "config": config_status,
            "components": health_status["components"],
        }

        status_code = 200 if health_status["status"] == "ok" else 503
        return jsonify(response), status_code

    except Exception as e:
        # Fallback to simple health check
        try:
            db_service = container.resolve("database_service")
            conn_ok = db_service.check_connection()
        except Exception:
            conn_ok = False

        return jsonify(
            {
                "status": "ok" if conn_ok else "error",
                "db": "ok" if conn_ok else "error",
                "config": "ok",
                "error": str(e),
            }
        ), (503 if not conn_ok else 200)


@bp.route("/metrics")
def metrics():
    """Enhanced metrics endpoint using core services."""
    try:
        container = get_container()
        metrics_service = container.resolve("metrics_service")
        metrics_data = metrics_service.get_metrics()

        return jsonify(metrics_data)

    except Exception:
        # Fallback to app-level metrics
        return jsonify(getattr(current_app, "metrics", {}))


@bp.route("/plugins")
@require_api_key
def plugins():
    """List available plugins and their instances."""
    registry = getattr(current_app, "plugin_registry", None)
    data = {"plugins": []}

    if registry is not None:
        for name in registry.list_plugins():
            instances = getattr(current_app, "config_data", {}).get(name, [])
            cls = registry.get(name)
            category = getattr(cls, "category", "plugins") if cls is not None else "plugins"
            description = getattr(cls, "description", "") if cls is not None else ""
            data["plugins"].append(
                {
                    "name": name,
                    "instances": instances,
                    "category": category,
                    "description": description,
                }
            )

    # Publish plugin list access event
    get_event_bus().publish_simple(
        "api.plugins.listed",
        data={"plugin_count": len(data["plugins"])},
        source="core_api",
    )

    return jsonify(data)


@bp.route("/plugins/<plugin_name>/validate/<int:idx>", methods=["POST"])
@require_api_key
def plugin_validate(plugin_name: str, idx: int):
    """Validate a specific plugin instance."""
    registry = getattr(current_app, "plugin_registry", None)
    if registry is None or registry.get(plugin_name) is None:
        return jsonify({"error": "unknown_plugin"}), 404

    instances = getattr(current_app, "config_data", {}).get(plugin_name, [])
    if idx < 0 or idx >= len(instances):
        return jsonify({"error": "invalid_instance"}), 400

    inst_cfg = instances[idx]

    try:
        pl = registry.create_instance(plugin_name, inst_cfg)
        result = pl.validate()

        # Publish validation event
        get_event_bus().publish_simple(
            Events.PLUGIN_LOADED if result else Events.PLUGIN_ERROR,
            data={"plugin": plugin_name, "instance": idx, "result": result},
            source="core_api",
        )

        return jsonify({"result": result})

    except Exception as e:
        current_app.logger.exception("Plugin validate failed: %s", e)

        # Publish validation error event
        get_event_bus().publish_simple(
            Events.PLUGIN_ERROR,
            data={"plugin": plugin_name, "instance": idx, "error": str(e)},
            source="core_api",
        )

        return jsonify({"error": "validate_failed", "msg": str(e)}), 500


@bp.route("/plugins/<plugin_name>/sync/<int:idx>", methods=["POST"])
@require_api_key
def plugin_sync(plugin_name: str, idx: int):
    """Sync/execute a specific plugin instance."""
    registry = getattr(current_app, "plugin_registry", None)
    if registry is None or registry.get(plugin_name) is None:
        return jsonify({"error": "unknown_plugin"}), 404

    instances = getattr(current_app, "config_data", {}).get(plugin_name, [])
    if idx < 0 or idx >= len(instances):
        return jsonify({"error": "invalid_instance"}), 400

    inst_cfg = instances[idx]

    try:
        pl = registry.create_instance(plugin_name, inst_cfg)

        # Publish job start event
        get_event_bus().publish_simple(
            Events.JOB_STARTED,
            data={"plugin": plugin_name, "instance": idx, "type": "sync"},
            source="core_api",
        )

        result = pl.sync()

        # Publish job completion event
        get_event_bus().publish_simple(
            Events.JOB_COMPLETED,
            data={
                "plugin": plugin_name,
                "instance": idx,
                "result": result,
                "type": "sync",
            },
            source="core_api",
        )

        return jsonify({"result": result})

    except Exception as e:
        current_app.logger.exception("Plugin sync failed: %s", e)

        # Publish job failure event
        get_event_bus().publish_simple(
            Events.JOB_FAILED,
            data={
                "plugin": plugin_name,
                "instance": idx,
                "error": str(e),
                "type": "sync",
            },
            source="core_api",
        )

        return jsonify({"error": "sync_failed", "msg": str(e)}), 500


@bp.route("/notifications/send", methods=["POST"])
@require_api_key
def notifications_send():
    """Send notification through apprise plugin."""
    # Simple pass-through to any apprise-backed plugin instance named 'apprise'
    data = request.get_json(force=True)

    # Find a configured apprise plugin instance
    registry = getattr(current_app, "plugin_registry", None)
    if registry is None or registry.get("apprise") is None:
        return jsonify({"error": "no_apprise_plugin"}), 404

    instances = getattr(current_app, "config_data", {}).get("apprise", [])
    if not instances:
        return jsonify({"error": "no_apprise_instances"}), 404

    try:
        pl = registry.create_instance("apprise", instances[0])

        # Expecting data to contain 'body' and optional 'title'
        title = data.get("title")
        body = data.get("body")
        if not body:
            return jsonify({"error": "missing_body"}), 400

        # Publish notification send event
        get_event_bus().publish_simple(
            "notification.send.started",
            data={
                "title": title,
                "body": body[:100] + "..." if len(body) > 100 else body,
            },
            source="core_api",
        )

        res = pl.send(title=title, body=body)

        # Publish notification result event
        get_event_bus().publish_simple(
            "notification.send.completed" if res else "notification.send.failed",
            data={"result": res, "title": title},
            source="core_api",
        )

        return jsonify({"result": res})

    except Exception as e:
        current_app.logger.exception("Apprise send failed: %s", e)

        # Publish notification error event
        get_event_bus().publish_simple(
            Events.ERROR_OCCURRED,
            data={"error": str(e), "operation": "notification_send"},
            source="core_api",
        )

        return jsonify({"error": "send_failed", "msg": str(e)}), 500


@bp.route("/openapi.json")
def openapi():
    """Return a minimal OpenAPI v3 JSON description for the API."""
    host = request.host or "localhost"
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "ResearchArr API",
            "version": "1.0.0",
            "description": (
                "Core API for ResearchArr: plugins, metrics, health, and notifications."
            ),
        },
        "servers": [{"url": f"http://{host}/api/v1"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "System is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "db": {"type": "string"},
                                            "config": {"type": "string"},
                                            "components": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        },
                        "503": {"description": "System is unhealthy"},
                    },
                }
            },
            "/metrics": {
                "get": {
                    "summary": "Application metrics",
                    "responses": {
                        "200": {
                            "description": "Current metrics",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "requests_total": {"type": "integer"},
                                            "errors_total": {"type": "integer"},
                                            "services": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/plugins": {
                "get": {
                    "summary": "List plugins",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {
                        "200": {
                            "description": "List of available plugins",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "plugins": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "instances": {"type": "array"},
                                                        "category": {"type": "string"},
                                                        "description": {"type": "string"},
                                                    },
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/plugins/{plugin}/validate/{idx}": {
                "post": {
                    "summary": "Validate plugin instance",
                    "security": [{"ApiKeyAuth": []}],
                    "parameters": [
                        {
                            "name": "plugin",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Plugin name",
                        },
                        {
                            "name": "idx",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "Instance index",
                        },
                    ],
                    "responses": {
                        "200": {"description": "Validation result"},
                        "404": {"description": "Plugin or instance not found"},
                        "500": {"description": "Validation failed"},
                    },
                }
            },
            "/plugins/{plugin}/sync/{idx}": {
                "post": {
                    "summary": "Execute plugin sync",
                    "security": [{"ApiKeyAuth": []}],
                    "parameters": [
                        {
                            "name": "plugin",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Plugin name",
                        },
                        {
                            "name": "idx",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "Instance index",
                        },
                    ],
                    "responses": {
                        "200": {"description": "Sync result"},
                        "404": {"description": "Plugin or instance not found"},
                        "500": {"description": "Sync failed"},
                    },
                }
            },
            "/notifications/send": {
                "post": {
                    "summary": "Send notification (apprise)",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "Notification title",
                                        },
                                        "body": {
                                            "type": "string",
                                            "description": "Notification body",
                                        },
                                    },
                                    "required": ["body"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Notification sent"},
                        "400": {"description": "Invalid request"},
                        "404": {"description": "Apprise plugin not available"},
                        "500": {"description": "Send failed"},
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for authentication",
                }
            }
        },
    }
    return jsonify(spec)


@bp.route("/docs")
@require_api_key_only
def docs():
    """Serve a minimal Swagger UI pointing at the OpenAPI JSON endpoint.

    This returns a small HTML page that loads Swagger UI from a CDN and
    configures it to fetch /api/v1/openapi.json. For security consider
    restricting access to authenticated users in production.
    """
    openapi_url = "/api/v1/openapi.json"
    html = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "    <head>\n"
        '        <meta charset="utf-8" />\n'
        '        <meta name="viewport"\n'
        '              content="width=device-width, initial-scale=1" />\n'
        "        <title>ResearchArr API Docs</title>\n"
        '        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4/'
        'swagger-ui.css" />\n'
        "    </head>\n"
        "    <body>\n"
        '        <div id="swagger-ui"></div>\n'
        '        <script src="https://unpkg.com/swagger-ui-dist@4/'
        'swagger-ui-bundle.js"></script>\n'
        "        <script>\n"
        "            window.onload = function() {\n"
        "                const ui = SwaggerUIBundle({\n"
        '                    url: "{{ openapi_url }}",\n'
        "                    dom_id: '#swagger-ui',\n"
        "                    presets: [SwaggerUIBundle.presets.apis],\n"
        "                    layout: 'BaseLayout',\n"
        "                })\n"
        "                window.ui = ui\n"
        "            }\n"
        "        </script>\n"
        "    </body>\n"
        "</html>\n"
    )
    return render_template_string(html, openapi_url=openapi_url)
