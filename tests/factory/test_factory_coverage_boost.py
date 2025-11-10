import json

from researcharr import factory

# Note: _parse_instances is defined inside create_app() and not exported at
# module level. We exercise its behavior indirectly via endpoints below.


def _login_client(client):
    # Helper to set logged_in session
    with client.session_transaction() as sess:
        sess["logged_in"] = True


def test_app_endpoints_and_apis(tmp_path):
    app = factory.create_app()
    app.testing = True
    client = app.test_client()

    # index should redirect to setup by default
    r = client.get("/")
    assert r.status_code in (302, 301, 200)

    # API version endpoint should work without login
    r = client.get("/api/version")
    assert r.status_code == 200
    data = r.get_json()
    assert "version" in data

    # POST tasks requires login
    _login_client(client)

    payload = {"action": "add", "task": {"name": "t"}}
    r = client.post("/api/tasks", data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 201)

    r = client.get("/api/storage")
    assert r.status_code == 200
    sdata = r.get_json()
    assert "paths" in sdata

    r = client.get("/api/logs?download=1")
    # likely 404 if no log present
    assert r.status_code in (200, 404, 401)

    # scheduling POST should accept form data
    r = client.post("/scheduling", data={"cron_schedule": "0 1 * * *"})
    assert r.status_code in (200, 302)
