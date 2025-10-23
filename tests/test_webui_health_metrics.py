
import pytest

from researcharr.factory import create_app

# Add client fixture for Flask test client

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def login(client, username="admin", password="researcharr"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

def test_health_endpoint(client):
    login(client)
    rv = client.get("/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["status"] == "ok"
    assert "db" in data and "config" in data and "threads" in data and "time" in data

def test_metrics_endpoint_increments(client):
    login(client)
    start = client.get("/metrics").get_json()["requests_total"]
    client.get("/health")
    after = client.get("/metrics").get_json()["requests_total"]
    assert after > start

def test_metrics_error_increment(client):
    login(client)
    # Trigger an error by requesting a non-existent route
    before = client.get("/metrics").get_json()["errors_total"]
    client.get("/doesnotexist")
    after = client.get("/metrics").get_json()["errors_total"]
    assert after > before

def test_loglevel_change_live(client):
    login(client)
    # Change loglevel to ERROR
    rv = client.post("/settings/general", data={"PUID": "1", "PGID": "1", "Timezone": "UTC", "LogLevel": "ERROR"}, follow_redirects=True)
    assert rv.status_code == 200
    # Change loglevel to DEBUG
    rv = client.post("/settings/general", data={"PUID": "1", "PGID": "1", "Timezone": "UTC", "LogLevel": "DEBUG"}, follow_redirects=True)
    assert rv.status_code == 200
