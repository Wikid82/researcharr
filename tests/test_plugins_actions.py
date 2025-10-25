import json

from researcharr.factory import create_app


def login_client(client):
    # Set the session value to simulate a logged-in user
    with client.session_transaction() as sess:
        sess["logged_in"] = True


def test_plugins_validate_and_sync(monkeypatch):
    app = create_app()
    # Ensure there's one configured sonarr instance
    app.config_data["sonarr"] = [
        {"name": "t", "url": "http://example", "api_key": "k", "enabled": True}
    ]
    client = app.test_client()
    login_client(client)
    # Validate
    resp = client.post("/api/plugins/sonarr/validate/0")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "result" in data
    # Sync
    resp = client.post("/api/plugins/sonarr/sync/0")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "result" in data


def test_api_plugins_requires_auth():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/plugins")
    assert resp.status_code == 401
    # now login
    login_client(client)
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "plugins" in data
