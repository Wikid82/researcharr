import json
import sqlite3

import pytest

from researcharr import factory


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    # Prepare a temporary DB and log file to exercise status/log checks
    db_file = tmp_path / "researcharr.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT)")
    conn.commit()
    conn.close()

    log_file = tmp_path / "app.log"
    log_file.write_text("line1\nline2\n")

    monkeypatch.setenv("RESEARCHARR_DB", str(db_file))
    monkeypatch.setenv("WEBUI_LOG", str(log_file))
    app = factory.create_app()
    app.testing = True
    client = app.test_client()
    return client


def test_setup_and_login_and_general(monkeypatch, app_client):
    client = app_client
    # Ensure webui.save_user_config is available and harmless
    monkeypatch.setattr(factory, "webui", factory, raising=False)

    # POST setup (create user) - minimal valid payload
    r = client.post(
        "/setup",
        data={"username": "admin", "password": "strongpass", "confirm": "strongpass"},
    )
    # can be redirect or render; accept 200/302
    assert r.status_code in (200, 302)

    # Login with default credentials (app uses in-memory defaults)
    r = client.post("/login", data={"username": "admin", "password": "password"})
    # On success should redirect to general settings
    assert r.status_code in (200, 302)

    # Regenerate API key via general settings (requires logged in session)
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    r = client.post("/settings/general", data={"regen_api": "1"})
    assert r.status_code in (200, 302)


def test_api_status_and_tasks_and_logs(app_client):
    client = app_client

    # API version should be accessible without login
    r = client.get("/api/version")
    assert r.status_code == 200
    j = r.get_json()
    assert "version" in j

    # Tasks POST requires authentication
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    payload = {"action": "add", "task": {"name": "t"}}
    r = client.post("/api/tasks", data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 201)

    # status endpoint (requires login)
    r = client.get("/api/status")
    assert r.status_code == 200
    s = r.get_json()
    assert "storage" in s and "db" in s

    # logs download - may be 200 or 404 depending on file presence
    r = client.get("/api/logs?download=1")
    assert r.status_code in (200, 404)
