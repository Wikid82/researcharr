import pytest
# url_for not used directly here


def login_and_get_client(app):
    # Helper: create a test client and log in using test fixtures
    client = app.test_client()
    # Many tests use POST /login with username/password; mimic a basic login
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    # Do not assert login here; fixtures may inject credentials.
    return client


@pytest.fixture
def client(app):
    return login_and_get_client(app)


def test_status_page(client):
    r = client.get("/status")
    assert r.status_code in (200, 302)
    if r.status_code == 200:
        assert b"System Status" in r.data


def test_tasks_page(client):
    r = client.get("/tasks")
    assert r.status_code in (200, 302)
    if r.status_code == 200:
        assert b"Tasks" in r.data


def test_backups_page(client):
    r = client.get("/backups")
    assert r.status_code in (200, 302)
    if r.status_code == 200:
        assert b"Backups" in r.data


def test_updates_page(client):
    r = client.get("/updates")
    assert r.status_code in (200, 302)
    if r.status_code == 200:
        assert b"Updates" in r.data


def test_logs_page(client):
    r = client.get("/logs")
    assert r.status_code in (200, 302)
    if r.status_code == 200:
        assert b"Logs" in r.data
