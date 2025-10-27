import io
import os
import zipfile
import yaml


def login_client(app):
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    return client


def test_backups_import_and_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()

    # create a backup zip that contains a config/config.yml to be restored
    zpath = backups_dir / "test_restore.zip"
    with zipfile.ZipFile(str(zpath), "w") as z:
        z.writestr("config/config.yml", "researcharr: {restored: true}\n")

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # ensure config does not exist yet
    cfg_file = tmp_path / "config.yml"
    if cfg_file.exists():
        cfg_file.unlink()

    # call restore
    r = client.post(f"/api/backups/restore/{zpath.name}")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("result") == "restored"
    # after restore, config.yml should exist with restored content
    assert cfg_file.exists()
    txt = cfg_file.read_text()
    assert "restored: true" in txt


def test_backups_download_and_delete_invalid_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # attempt path traversal download
    r = client.get("/api/backups/download/../etc/passwd")
    assert r.status_code == 400
    j = r.get_json()
    assert j.get("error") == "invalid_name"

    # attempt delete of non-existent file
    r2 = client.delete("/api/backups/delete/missing.zip")
    assert r2.status_code == 404
    assert r2.get_json().get("error") == "not_found"


def test_backups_settings_get_and_post(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # GET current (should return dict)
    r = client.get("/api/backups/settings")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)

    # POST update settings
    payload = {"retain_count": 3, "retain_days": 7, "pre_restore": False}
    r2 = client.post("/api/backups/settings", json=payload)
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert j2.get("result") == "ok"

    # persisted file should exist
    cfg_file = tmp_path / "backups.yml"
    assert cfg_file.exists()
    cfg = yaml.safe_load(cfg_file.read_text())
    assert cfg.get("retain_count") == 3
