from flask import Flask
from werkzeug.security import generate_password_hash


def make_app(api_module, *, with_api_key: bool = False, with_registry: bool = False, metrics_stub: bool = False):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")

    # Optional API key configuration for protected endpoints
    if with_api_key:
        app.config_data = {  # type: ignore[attr-defined]
            "general": {"api_key_hash": generate_password_hash("test-token")}
        }
    else:
        app.config_data = {}  # type: ignore[attr-defined]

    # Optional plugin registry stub
    if with_registry:
        class _Registry:
            def __init__(self):
                self._instances = {}
            def list_plugins(self):
                return list(self._instances.keys())
            def get(self, name):
                return object if name in self._instances else None
            def create_instance(self, name, cfg):
                if name not in self._instances:
                    raise KeyError("unknown")
                return self._instances[name]
            def _seed(self, name, inst):
                self._instances[name] = inst
        app.plugin_registry = _Registry()  # type: ignore[attr-defined]

    # Optional metrics service via container stub
    if metrics_stub:
        class _Metrics:
            def get_metrics(self):
                return {"requests_total": 1, "errors_total": 0, "services": {}}
        class _Container:
            def resolve(self, name):
                if name == "metrics_service":
                    return _Metrics()
                raise KeyError(name)
        # Patch get_container on the api module
        api_module.get_container = lambda: _Container()  # type: ignore[attr-defined]

    app.register_blueprint(api_module.bp, url_prefix="/api/v1")
    return app


def test_openapi_json_endpoint():
    from researcharr.core import api as core_api
    app = make_app(core_api)
    with app.test_client() as c:
        r = c.get("/api/v1/openapi.json")
        assert r.status_code == 200
        data = r.get_json()
        assert data["openapi"] == "3.0.0"
        assert "/health" in data["paths"]


def test_docs_endpoint_protected_with_api_key():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True)
    with app.test_client() as c:
        r = c.get("/api/v1/docs", headers={"X-API-Key": "test-token"})
        assert r.status_code == 200
        assert b"SwaggerUI" in r.data or b"swagger-ui" in r.data


def test_metrics_with_container_stub():
    from researcharr.core import api as core_api
    app = make_app(core_api, metrics_stub=True)
    with app.test_client() as c:
        r = c.get("/api/v1/metrics")
        assert r.status_code == 200
        data = r.get_json()
        assert "requests_total" in data


def test_plugins_list_with_api_key_and_registry():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True, with_registry=True)
    with app.test_client() as c:
        r = c.get("/api/v1/plugins", headers={"X-API-Key": "test-token"})
        assert r.status_code == 200
        data = r.get_json()
        assert "plugins" in data


def test_plugins_list_with_session_cookie_allows_access():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=False, with_registry=True)
    # Emulate session cookie fallback path
    app.session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")  # type: ignore[attr-defined]
    with app.test_client() as c:
        c.set_cookie(app.session_cookie_name, "dummy")  # type: ignore[arg-type]
        r = c.get("/api/v1/plugins")
        assert r.status_code == 200


def test_plugin_validate_success_and_failure():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True, with_registry=True)
    # Seed plugin registry and config
    class _Plugin:
        def __init__(self, cfg, result=True):
            self._result = result
        def validate(self):
            return self._result
    pr = app.plugin_registry  # type: ignore[attr-defined]
    pr._seed("mypl", _Plugin({}, result=True))
    app.config_data["mypl"] = [{}, {}]  # type: ignore[attr-defined]
    with app.test_client() as c:
        ok = c.post("/api/v1/plugins/mypl/validate/0", headers={"X-API-Key": "test-token"})
        assert ok.status_code == 200
        bad = c.post("/api/v1/plugins/mypl/validate/1", headers={"X-API-Key": "test-token"})
        assert bad.status_code == 200


def test_plugin_validate_exception_path():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True, with_registry=True)
    class _Plugin:
        def __init__(self, cfg):
            pass
        def validate(self):
            raise RuntimeError("boom")
    pr = app.plugin_registry  # type: ignore[attr-defined]
    pr._seed("mypl", _Plugin({}))
    app.config_data["mypl"] = [{}]  # type: ignore[attr-defined]
    with app.test_client() as c:
        r = c.post("/api/v1/plugins/mypl/validate/0", headers={"X-API-Key": "test-token"})
        assert r.status_code == 500


def test_plugin_sync_success_and_failure():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True, with_registry=True)
    class _PluginOK:
        def __init__(self, cfg):
            pass
        def sync(self):
            return {"ok": True}
    class _PluginFail:
        def __init__(self, cfg):
            pass
        def sync(self):
            raise RuntimeError("fail")
    pr = app.plugin_registry  # type: ignore[attr-defined]
    pr._seed("ok", _PluginOK({}))
    pr._seed("bad", _PluginFail({}))
    app.config_data["ok"] = [{}]  # type: ignore[attr-defined]
    app.config_data["bad"] = [{}]  # type: ignore[attr-defined]
    with app.test_client() as c:
        r1 = c.post("/api/v1/plugins/ok/sync/0", headers={"X-API-Key": "test-token"})
        assert r1.status_code == 200
        r2 = c.post("/api/v1/plugins/bad/sync/0", headers={"X-API-Key": "test-token"})
        assert r2.status_code == 500


def test_notifications_send_success_and_missing_plugin():
    from researcharr.core import api as core_api
    app = make_app(core_api, with_api_key=True, with_registry=True)

    class Apprise:
        def __init__(self, cfg):
            pass
        def send(self, title=None, body=None):
            return True
    pr = app.plugin_registry  # type: ignore[attr-defined]
    pr._seed("apprise", Apprise({}))
    app.config_data["apprise"] = [{}]  # type: ignore[attr-defined]
    with app.test_client() as c:
        ok = c.post("/api/v1/notifications/send", json={"title": "t", "body": "b"}, headers={"X-API-Key": "test-token"})
        assert ok.status_code == 200

    # New app without apprise seeded
    app2 = make_app(core_api, with_api_key=True, with_registry=True)
    with app2.test_client() as c2:
        not_found = c2.post("/api/v1/notifications/send", json={"body": "b"}, headers={"X-API-Key": "test-token"})
        assert not_found.status_code == 404
