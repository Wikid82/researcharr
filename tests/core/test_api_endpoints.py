from typing import Any, cast

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

# Import api directly from researcharr package
from researcharr import api


class DummyRegistry:
    def __init__(self, plugins=None):
        self._plugins = plugins or {}

    def list_plugins(self):
        return list(self._plugins.keys())

    def get(self, name):
        return self._plugins.get(name)

    def create_instance(self, name, cfg):
        cls = self.get(name)
        if cls is None:
            raise KeyError(name)
        # If cls is a class, instantiate it; if it's already an instance, return it
        if isinstance(cls, type):
            return cls(cfg)
        return cls


class DummyPlugin:
    category = "plugins"
    description = "dummy"

    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    def validate(self):
        return True

    def sync(self):
        return {"synced": True}

    def send(self, title=None, body=None):
        if not body:
            raise ValueError("missing body")
        return {"sent": True, "title": title, "body": body}


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(api.bp, url_prefix="/api/v1")
    yield app


def test_health_and_metrics(app):
    app.metrics = {"jobs": 3}
    with app.test_client() as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] in ("ok", "error")

        r = c.get("/api/v1/metrics")
        assert r.status_code == 200
        assert r.get_json() == {"jobs": 3}


def test_openapi_and_docs_require_key(app):
    # set API key
    key = "sekrit"
    app.config_data = cast(
        dict[str, Any], {"general": {"api_key_hash": generate_password_hash(key)}}
    )
    with app.test_client() as c:
        # openapi is public
        r = c.get("/api/v1/openapi.json")
        assert r.status_code == 200
        assert r.get_json().get("openapi") == "3.0.0"

        # docs requires API key only
        r = c.get("/api/v1/docs")
        assert r.status_code == 401

        r = c.get("/api/v1/docs", headers={"X-API-Key": key})
        assert r.status_code == 200
        assert b"swagger-ui" in r.data


def test_plugins_and_validation_and_sync_and_notifications(app):
    key = "api123"
    app.config_data = cast(
        dict[str, Any], {"general": {"api_key_hash": generate_password_hash(key)}}
    )
    app.config_data = cast(
        dict[str, Any], {"general": {"api_key_hash": generate_password_hash(key)}}
    )

    # register dummy plugin
    app.plugin_registry = DummyRegistry({"apprise": DummyPlugin, "dummy": DummyPlugin})
    # config_data lists instances
    app.config_data.update({"apprise": [{"name": "ap1"}], "dummy": [{"name": "d1"}]})

    with app.test_client() as c:
        # plugins listing
        r = c.get("/api/v1/plugins", headers={"X-API-Key": key})
        assert r.status_code == 200
        plugins = r.get_json()["plugins"]
        assert any(p["name"] == "apprise" for p in plugins)

        # validate success
        r = c.post("/api/v1/plugins/dummy/validate/0", headers={"X-API-Key": key})
        assert r.status_code == 200
        assert r.get_json()["result"] is True

        # sync success
        r = c.post("/api/v1/plugins/dummy/sync/0", headers={"X-API-Key": key})
        assert r.status_code == 200
        assert r.get_json()["result"]["synced"] is True

        # notifications missing body
        r = c.post("/api/v1/notifications/send", headers={"X-API-Key": key}, json={})
        assert r.status_code == 400

        # notifications success
        r = c.post(
            "/api/v1/notifications/send",
            headers={"X-API-Key": key},
            json={"body": "hi", "title": "t"},
        )
        assert r.status_code == 200
        assert r.get_json()["result"]["sent"] is True


def test_plugin_not_found_and_invalid_index(app):
    key = "k"
    app.config_data = cast(
        dict[str, Any], {"general": {"api_key_hash": generate_password_hash(key)}}
    )
    app.plugin_registry = DummyRegistry({})
    app.config_data = cast(
        dict[str, Any], {"general": {"api_key_hash": generate_password_hash(key)}}
    )
    app.plugin_registry = DummyRegistry({})
    app.config_data.update({"dummy": []})
    with app.test_client() as c:

        # invalid index
        app.plugin_registry = DummyRegistry({"dummy": DummyPlugin})
        app.config_data.update({"dummy": []})
        r = c.post("/api/v1/plugins/dummy/validate/10", headers={"X-API-Key": key})
        assert r.status_code == 400
