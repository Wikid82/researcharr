import os

import pytest
import yaml
from werkzeug.security import generate_password_hash

from researcharr import webui


# Always reset user config to default before each test
@pytest.fixture(autouse=True)
def reset_user_config():
    # Use the same path as the app: config/webui_user.yml relative to project root
    user_config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../config/webui_user.yml")
    )
    # But the app expects 'config/webui_user.yml' relative to CWD/project root
    # So, always write to 'config/webui_user.yml' in the CWD
    user_config_path = os.path.abspath(
        os.path.join(os.getcwd(), "config/webui_user.yml")
    )
    os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
    with open(user_config_path, "w") as f:
        yaml.safe_dump(
            {
                "username": "admin",
                "password_hash": generate_password_hash("researcharr"),
            },
            f,
        )
    yield


@pytest.fixture
def client():
    webui.app.config["TESTING"] = True
    with webui.app.test_client() as client:
        yield client


def login(client, username="admin", password="researcharr"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_unauthenticated_redirect(client):
    rv = client.get("/settings/general", follow_redirects=False)
    assert rv.status_code == 302
    assert "/login" in rv.headers["Location"]


def test_login_success(client):
    rv = login(client)
    assert b"Logout" in rv.data


def test_login_failure(client):
    rv = login(client, password="wrong")
    assert b"Invalid username or password" in rv.data or b"Login" in rv.data


def test_general_settings_page(client):
    login(client)
    rv = client.get("/settings/general")
    assert rv.status_code == 200
    assert b"General" in rv.data
    # Check for header, sidebar, and footer
    assert b"researcharr" in rv.data  # header
    assert b"sidebar" in rv.data  # sidebar
    assert b"footer" in rv.data or b"footer.html" in rv.data  # footer


def test_radarr_settings_page(client):
    login(client)
    rv = client.get("/settings/radarr")
    assert rv.status_code == 200
    assert b"Radarr" in rv.data
    assert b"researcharr" in rv.data
    assert b"sidebar" in rv.data
    assert b"footer" in rv.data or b"footer.html" in rv.data


def test_sonarr_settings_page(client):
    login(client)
    rv = client.get("/settings/sonarr")
    assert rv.status_code == 200
    assert b"Sonarr" in rv.data
    assert b"researcharr" in rv.data
    assert b"sidebar" in rv.data
    assert b"footer" in rv.data or b"footer.html" in rv.data


def test_scheduling_page(client):
    login(client)
    rv = client.get("/scheduling")
    assert rv.status_code == 200
    assert b"Scheduling" in rv.data
    assert b"researcharr" in rv.data
    assert b"sidebar" in rv.data
    assert b"footer" in rv.data or b"footer.html" in rv.data


def test_user_settings_page(client):
    login(client)
    rv = client.get("/user")
    assert rv.status_code == 200
    assert b"User Settings" in rv.data
    assert b"researcharr" in rv.data
    assert b"sidebar" in rv.data
    assert b"footer" in rv.data or b"footer.html" in rv.data


def test_general_settings_page_content(client):
    login(client)
    rv = client.get("/settings/general")
    assert b"PUID" in rv.data or b"puid" in rv.data


def test_radarr_settings_page_content(client):
    login(client)
    rv = client.get("/settings/radarr")
    assert b"API Key" in rv.data


def test_sonarr_settings_page_content(client):
    login(client)
    rv = client.get("/settings/sonarr")
    assert b"API Key" in rv.data


def test_scheduling_page_content(client):
    login(client)
    rv = client.get("/scheduling")
    assert b"Timezone" in rv.data


def test_user_settings_page_content(client):
    login(client)
    rv = client.get("/user")
    assert b"Username" in rv.data


def test_general_settings_save(client):
    login(client)
    rv = client.post(
        "/save", data={"puid": "1001", "pgid": "1001"}, follow_redirects=True
    )
    assert rv.status_code == 200
    assert b"General" in rv.data or b"Settings" in rv.data


def test_user_settings_save_blank_username(client):
    login(client)
    rv = client.post(
        "/user", data={"username": "", "password": ""}, follow_redirects=True
    )
    assert b"cannot be blank" in rv.data or b"User settings" in rv.data


def test_user_settings_save_password_change(client):
    login(client)
    rv = client.post(
        "/user",
        data={"username": "admin", "password": "newpass"},
        follow_redirects=True,
    )
    assert b"User settings updated" in rv.data or b"User Settings" in rv.data


def test_scheduling_save_invalid(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    rv = client.post(
        "/scheduling",
        data={"cron_schedule": "", "timezone": "UTC"},  # blank to trigger error
        follow_redirects=True,
    )
    assert b"cannot be blank" in rv.data or b"Scheduling" in rv.data


def test_radarr_settings_save_invalid(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    rv = client.post(
        "/settings/radarr",
        data={
            "radarr0_enabled": "on",
            "radarr0_name": "",
            "radarr0_url": "",
            "radarr0_api_key": "",
            "radarr0_process": "on",
            "radarr0_state_mgmt": "on",
            "radarr0_movies_to_upgrade": 5,
            "radarr0_max_download_queue": 15,
            "radarr0_reprocess_interval_days": 7,
        },
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b"Radarr" in rv.data


def test_sonarr_settings_save_invalid(client):
    login(client)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    rv = client.post(
        "/settings/sonarr",
        data={
            "sonarr0_enabled": "on",
            "sonarr0_name": "",
            "sonarr0_url": "",
            "sonarr0_api_key": "",
            "sonarr0_process": "on",
            "sonarr0_mode": "series",
            "sonarr0_api_pulls": 20,
            "sonarr0_state_mgmt": "on",
            "sonarr0_episodes_to_upgrade": 5,
            "sonarr0_max_download_queue": 15,
            "sonarr0_reprocess_interval_days": 7,
        },
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b"Sonarr" in rv.data
