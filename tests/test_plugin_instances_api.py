import json
import yaml

from researcharr.factory import create_app


def login_client(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True


def test_add_update_delete_plugin_instance(tmp_path, monkeypatch):
    # Use a temp CONFIG_DIR so we don't touch the real /config on hosts
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    app = create_app()
    app.config["TESTING"] = True

    # seed empty plugin list
    app.config_data["sonarr"] = []

    client = app.test_client()
    login_client(client)

    # Add instance
    payload = {
        "action": "add",
        "instance": {"name": "T", "url": "http://x", "api_key": "k", "enabled": True},
    }
    resp = client.post(
        "/api/plugins/sonarr/instances",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.data
    assert len(app.config_data["sonarr"]) == 1

    # Check that file exists and contains the instance
    cfg_file = tmp_path / "plugins" / "sonarr.yml"
    assert cfg_file.exists()
    data = yaml.safe_load(cfg_file.read_text())
    assert isinstance(data, list)
    assert any(i.get("name") == "T" for i in data)

    # Update instance (index 0)
    payload = {
        "action": "update",
        "idx": 0,
        "instance": {"name": "T2", "url": "http://x", "api_key": "k", "enabled": True},
    }
    resp = client.post(
        "/api/plugins/sonarr/instances",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = yaml.safe_load(cfg_file.read_text())
    assert any(i.get("name") == "T2" for i in data)

    # Delete instance
    payload = {"action": "delete", "idx": 0}
    resp = client.post(
        "/api/plugins/sonarr/instances",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = yaml.safe_load(cfg_file.read_text())
    assert data == [] or not data


def test_instance_validation_errors(tmp_path, monkeypatch):
    # missing required fields should return 400 and not write file
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    app = create_app()
    app.config["TESTING"] = True
    app.config_data["sonarr"] = []
    client = app.test_client()
    login_client(client)

    # Missing name/url/api_key when enabled
    payload = {
        "action": "add",
        "instance": {"name": "", "url": "", "api_key": "", "enabled": True},
    }
    resp = client.post(
        "/api/plugins/sonarr/instances",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code >= 400
    cfg_dir = tmp_path / "plugins"
    # file should either not exist or be empty
    cfg_file = cfg_dir / "sonarr.yml"
    assert not cfg_file.exists()
