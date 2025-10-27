from werkzeug.security import generate_password_hash


def login_client(app):
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    return client


def test_openapi_and_docs_require_api_key(monkeypatch):
    from researcharr.factory import create_app

    app = create_app()
    client = app.test_client()

    # openapi.json is public
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("openapi") == "3.0.0"

    # docs endpoint requires API key only
    # without header should be unauthorized
    r2 = client.get("/api/v1/docs")
    assert r2.status_code == 401

    # set a valid api key hash in app config and call with header
    secret = "sekrit"
    app.config_data.setdefault("general", {})["api_key_hash"] = generate_password_hash(secret)
    r3 = client.get("/api/v1/docs", headers={"X-API-Key": secret})
    assert r3.status_code == 200
    assert "ResearchArr API Docs" in r3.data.decode("utf-8")


def test_plugins_and_validate_and_notifications(monkeypatch):
    from researcharr.factory import create_app

    app = create_app()
    client = app.test_client()

    # prepare api key
    secret = "token"
    app.config_data.setdefault("general", {})["api_key_hash"] = generate_password_hash(secret)

    # without header -> unauthorized
    r = client.get("/api/v1/plugins")
    assert r.status_code == 401

    # with header and no registry -> empty plugins
    r2 = client.get("/api/v1/plugins", headers={"X-API-Key": secret})
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert "plugins" in j2

    # plugin validate unknown plugin -> 404
    r3 = client.post("/api/v1/plugins/nope/validate/0", headers={"X-API-Key": secret})
    assert r3.status_code == 404

    # test notifications send when no apprise plugin registered -> 404
    r4 = client.post("/api/v1/notifications/send", headers={"X-API-Key": secret}, json={"body": "x"})
    assert r4.status_code == 404

    # Now mock a simple plugin registry with apprise
    class DummyRegistry:
        def __init__(self):
            self._map = {"apprise": object}

        def list_plugins(self):
            return ["apprise"]

        def get(self, name):
            return object

        def create_instance(self, name, cfg):
            class DummyApprise:
                def send(self, title=None, body=None):
                    return True

            return DummyApprise()

    app.plugin_registry = DummyRegistry()
    # ensure there's an apprise instance config
    app.config_data.setdefault("apprise", []).append({"name": "a"})

    # sending without body should return 400
    r5 = client.post("/api/v1/notifications/send", headers={"X-API-Key": secret}, json={})
    assert r5.status_code == 400

    # with body should succeed
    r6 = client.post("/api/v1/notifications/send", headers={"X-API-Key": secret}, json={"body": "hello"})
    assert r6.status_code == 200
    assert r6.get_json().get("result") is True
