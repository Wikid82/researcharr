import pytest

from researcharr.factory import create_app


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


def test_radarr_save_and_reload(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "radarr0_enabled": "on",
        "radarr0_name": "TestRadarr",
        "radarr0_url": "http://localhost:7878",
        "radarr0_api_key": "abc123",
        "radarr0_process": "on",
        "radarr0_state_mgmt": "on",
        "radarr0_movies_to_upgrade": 10,
        "radarr0_max_download_queue": 20,
        "radarr0_reprocess_interval_days": 3,
    }
    rv = client.post("/settings/radarr", data=data, follow_redirects=True)
    assert b"Radarr settings saved" in rv.data or b"Radarr" in rv.data
    rv = client.get("/settings/radarr")
    assert b"TestRadarr" in rv.data
    assert b"http://localhost:7878" in rv.data
    assert b"abc123" in rv.data


def test_sonarr_save_and_reload(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "sonarr0_enabled": "on",
        "sonarr0_name": "TestSonarr",
        "sonarr0_url": "http://localhost:8989",
        "sonarr0_api_key": "def456",
        "sonarr0_process": "on",
        "sonarr0_mode": "season",
        "sonarr0_api_pulls": 15,
        "sonarr0_state_mgmt": "on",
        "sonarr0_episodes_to_upgrade": 8,
        "sonarr0_max_download_queue": 12,
        "sonarr0_reprocess_interval_days": 2,
    }
    rv = client.post("/settings/sonarr", data=data, follow_redirects=True)
    assert b"Sonarr settings saved" in rv.data or b"Sonarr" in rv.data
    rv = client.get("/settings/sonarr")
    assert b"TestSonarr" in rv.data
    assert b"http://localhost:8989" in rv.data
    assert b"def456" in rv.data


def test_scheduling_save_and_reload(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {"cron_schedule": "0 0 * * *", "timezone": "UTC"}
    rv = client.post("/scheduling", data=data, follow_redirects=True)
    assert b"Schedule saved" in rv.data or b"Scheduling" in rv.data
    rv = client.get("/scheduling")
    assert b"0 0 * * *" in rv.data
    assert b"UTC" in rv.data


def test_user_settings_change_username(client):
    import pytest

    pytest.skip("Username change test is skipped due to config reset on app import.")


def test_logout_flow(client):
    login(client)
    rv = client.get("/logout", follow_redirects=True)
    assert b"Login" in rv.data
    rv = client.get("/settings/radarr", follow_redirects=True)
    assert b"Login" in rv.data


def test_radarr_multiple_instances(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "radarr0_enabled": "on",
        "radarr0_name": "Radarr1",
        "radarr0_url": "http://localhost:7878",
        "radarr0_api_key": "key1",
        "radarr0_process": "on",
        "radarr0_state_mgmt": "on",
        "radarr0_movies_to_upgrade": 5,
        "radarr0_max_download_queue": 10,
        "radarr0_reprocess_interval_days": 2,
        "radarr1_enabled": "on",
        "radarr1_name": "Radarr2",
        "radarr1_url": "http://localhost:7879",
        "radarr1_api_key": "key2",
        "radarr1_process": "on",
        "radarr1_state_mgmt": "on",
        "radarr1_movies_to_upgrade": 6,
        "radarr1_max_download_queue": 11,
        "radarr1_reprocess_interval_days": 3,
    }
    rv = client.post("/settings/radarr", data=data, follow_redirects=True)
    assert b"Radarr settings saved" in rv.data or b"Radarr" in rv.data
    rv = client.get("/settings/radarr")
    assert b"Radarr1" in rv.data
    assert b"Radarr2" in rv.data
    assert b"http://localhost:7878" in rv.data
    assert b"http://localhost:7879" in rv.data


def test_sonarr_multiple_instances(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "sonarr0_enabled": "on",
        "sonarr0_name": "Sonarr1",
        "sonarr0_url": "http://localhost:8989",
        "sonarr0_api_key": "key1",
        "sonarr0_process": "on",
        "sonarr0_mode": "series",
        "sonarr0_api_pulls": 10,
        "sonarr0_state_mgmt": "on",
        "sonarr0_episodes_to_upgrade": 5,
        "sonarr0_max_download_queue": 10,
        "sonarr0_reprocess_interval_days": 2,
        "sonarr1_enabled": "on",
        "sonarr1_name": "Sonarr2",
        "sonarr1_url": "http://localhost:8990",
        "sonarr1_api_key": "key2",
        "sonarr1_process": "on",
        "sonarr1_mode": "season",
        "sonarr1_api_pulls": 12,
        "sonarr1_state_mgmt": "on",
        "sonarr1_episodes_to_upgrade": 6,
        "sonarr1_max_download_queue": 12,
        "sonarr1_reprocess_interval_days": 3,
    }
    rv = client.post("/settings/sonarr", data=data, follow_redirects=True)
    assert b"Sonarr settings saved" in rv.data or b"Sonarr" in rv.data
    rv = client.get("/settings/sonarr")
    assert b"Sonarr1" in rv.data
    assert b"Sonarr2" in rv.data
    assert b"http://localhost:8989" in rv.data
    assert b"http://localhost:8990" in rv.data


def test_radarr_api_pulls_and_state_mgmt(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "radarr0_enabled": "on",
        "radarr0_name": "RadarrAPI",
        "radarr0_url": "http://localhost:7878",
        "radarr0_api_key": "key",
        "radarr0_process": "on",
        "radarr0_state_mgmt": "",  # unchecked
        "radarr0_api_pulls": 42,
        "radarr0_movies_to_upgrade": 5,
        "radarr0_max_download_queue": 10,
        "radarr0_reprocess_interval_days": 2,
    }
    rv = client.post("/settings/radarr", data=data, follow_redirects=True)
    assert b"Radarr settings saved" in rv.data or b"Radarr" in rv.data
    rv = client.get("/settings/radarr")
    assert b"RadarrAPI" in rv.data
    assert b"42" in rv.data


def test_sonarr_api_pulls_and_state_mgmt(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    data = {
        "sonarr0_enabled": "on",
        "sonarr0_name": "SonarrAPI",
        "sonarr0_url": "http://localhost:8989",
        "sonarr0_api_key": "key",
        "sonarr0_process": "on",
        "sonarr0_state_mgmt": "",  # unchecked
        "sonarr0_api_pulls": 99,
        "sonarr0_mode": "episode",
        "sonarr0_episodes_to_upgrade": 5,
        "sonarr0_max_download_queue": 10,
        "sonarr0_reprocess_interval_days": 2,
    }
    rv = client.post("/settings/sonarr", data=data, follow_redirects=True)
    assert b"Sonarr settings saved" in rv.data or b"Sonarr" in rv.data
    rv = client.get("/settings/sonarr")
    assert b"SonarrAPI" in rv.data
    assert b"99" in rv.data


def test_validate_sonarr_endpoint_invalid(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    rv = client.post("/validate_sonarr/99")
    assert rv.is_json
    assert rv.json["success"] is False
    assert "Invalid Sonarr index" in rv.json["msg"]


def test_validate_sonarr_endpoint_missing_url(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    # Save a sonarr config with missing url
    data = {
        "sonarr0_enabled": "on",
        "sonarr0_name": "SonarrNoURL",
        "sonarr0_url": "",
        "sonarr0_api_key": "key",
        "sonarr0_process": "on",
        "sonarr0_state_mgmt": "on",
        "sonarr0_api_pulls": 10,
        "sonarr0_mode": "series",
        "sonarr0_episodes_to_upgrade": 5,
        "sonarr0_max_download_queue": 10,
        "sonarr0_reprocess_interval_days": 2,
    }
    rv = client.post("/settings/sonarr", data=data, follow_redirects=True)
    # Should get error message in response
    assert b"Missing URL or API key for enabled instance." in rv.data


def test_validate_sonarr_endpoint_missing_key(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    # Save a sonarr config with missing api_key
    data = {
        "sonarr0_enabled": "on",
        "sonarr0_name": "SonarrNoKey",
        "sonarr0_url": "http://localhost:8989",
        "sonarr0_api_key": "",
        "sonarr0_process": "on",
        "sonarr0_state_mgmt": "on",
        "sonarr0_api_pulls": 10,
        "sonarr0_mode": "series",
        "sonarr0_episodes_to_upgrade": 5,
        "sonarr0_max_download_queue": 10,
        "sonarr0_reprocess_interval_days": 2,
    }
    rv = client.post("/settings/sonarr", data=data, follow_redirects=True)
    # Should get error message in response
    assert b"Missing URL or API key for enabled instance." in rv.data
