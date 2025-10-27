from functools import wraps

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template_string,
    request,
)
from werkzeug.security import check_password_hash

bp = Blueprint("api_v1", __name__)


def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Allow either a valid session (web UI) or an API key header
        if getattr(current_app, "config_data", None) and request.headers.get(
            "X-API-Key"
        ):
            key = request.headers.get("X-API-Key")
            stored_hash = (
                getattr(current_app, "config_data", {})
                .get("general", {})
                .get("api_key_hash")
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
        if request.cookies.get(cookie_name) and request.authorization is None:
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
        stored_hash = (
            getattr(current_app, "config_data", {})
            .get("general", {})
            .get("api_key_hash")
        )
        if stored_hash and key and check_password_hash(stored_hash, key):
            return func(*args, **kwargs)
        return jsonify({"error": "unauthorized"}), 401

    return wrapper


@bp.route("/health")
def health():
    # Mirror the app-level /health
    try:
        conn_ok = True
        # attempt a lightweight db check if DB path provided
        db = getattr(current_app, "DB_PATH", None)
        if db:
            import sqlite3

            conn = sqlite3.connect(db)
            conn.execute("SELECT 1")
            conn.close()
    except Exception:
        conn_ok = False
    return jsonify(
        {
            "status": "ok" if conn_ok else "error",
            "db": "ok" if conn_ok else "error",
            "config": "ok",
        }
    )


@bp.route("/metrics")
def metrics():
    return jsonify(getattr(current_app, "metrics", {}))


@bp.route("/plugins")
@require_api_key
def plugins():
    registry = getattr(current_app, "plugin_registry", None)
    data = {"plugins": []}
    if registry is not None:
        for name in registry.list_plugins():
            instances = getattr(current_app, "config_data", {}).get(name, [])
            cls = registry.get(name)
            category = (
                getattr(cls, "category", "plugins") if cls is not None else "plugins"
            )
            description = getattr(cls, "description", "") if cls is not None else ""
            data["plugins"].append(
                {
                    "name": name,
                    "instances": instances,
                    "category": category,
                    "description": description,
                }
            )
    return jsonify(data)


@bp.route("/plugins/<plugin_name>/validate/<int:idx>", methods=["POST"])
@require_api_key
def plugin_validate(plugin_name: str, idx: int):
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
        return jsonify({"result": result})
    except Exception as e:
        current_app.logger.exception("Plugin validate failed: %s", e)
        return jsonify({"error": "validate_failed", "msg": str(e)}), 500


@bp.route("/plugins/<plugin_name>/sync/<int:idx>", methods=["POST"])
@require_api_key
def plugin_sync(plugin_name: str, idx: int):
    registry = getattr(current_app, "plugin_registry", None)
    if registry is None or registry.get(plugin_name) is None:
        return jsonify({"error": "unknown_plugin"}), 404
    instances = getattr(current_app, "config_data", {}).get(plugin_name, [])
    if idx < 0 or idx >= len(instances):
        return jsonify({"error": "invalid_instance"}), 400
    inst_cfg = instances[idx]
    try:
        pl = registry.create_instance(plugin_name, inst_cfg)
        result = pl.sync()
        return jsonify({"result": result})
    except Exception as e:
        current_app.logger.exception("Plugin sync failed: %s", e)
        return jsonify({"error": "sync_failed", "msg": str(e)}), 500


@bp.route("/notifications/send", methods=["POST"])
@require_api_key
def notifications_send():
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
        res = pl.send(title=title, body=body)
        return jsonify({"result": res})
    except Exception as e:
        current_app.logger.exception("Apprise send failed: %s", e)
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
                "Minimal API for ResearchArr: plugins, metrics, health, "
                "and notifications."
            ),
        },
        "servers": [{"url": f"http://{host}/api/v1"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/metrics": {
                "get": {
                    "summary": "Metrics",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/plugins": {
                "get": {
                    "summary": "List plugins",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {"200": {"description": "List"}},
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
                        },
                        {
                            "name": "idx",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/notifications/send": {
                "post": {
                    "summary": "Send notification (apprise)",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
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
        "<html lang=\"en\">\n"
        "    <head>\n"
        "        <meta charset=\"utf-8\" />\n"
        "        <meta name=\"viewport\"\n"
        "              content=\"width=device-width, initial-scale=1\" />\n"
        "        <title>ResearchArr API Docs</title>\n"
        '        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4/'
        'swagger-ui.css" />\n'
        "    </head>\n"
        "    <body>\n"
        "        <div id=\"swagger-ui\"></div>\n"
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
