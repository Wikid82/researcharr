import os
import re

import yaml

from researcharr import webui


def test_load_user_config_creates_file_and_logs_password(tmp_path, caplog, monkeypatch):
    # Point USER_CONFIG_PATH to a temp file
    cfg = tmp_path / "webui_user.yml"
    monkeypatch.setattr(webui, "USER_CONFIG_PATH", str(cfg), raising=False)

    # Capture logs
    caplog.set_level("INFO", logger="researcharr")

    # Ensure file does not exist
    if cfg.exists():
        cfg.unlink()

    # Call loader which should create the file and log the generated password
    data = webui.load_user_config()

    assert cfg.exists()
    assert isinstance(data, dict)
    assert data.get("username") == "researcharr"
    assert "password_hash" in data

    # Check caplog for the generated password message
    msgs = [r.message for r in caplog.records if r.name == "researcharr"]
    assert any("Generated web UI initial password" in m for m in msgs)


def test_save_user_config_writes_hash(tmp_path, monkeypatch):
    cfg = tmp_path / "webui_user.yml"
    monkeypatch.setattr(webui, "USER_CONFIG_PATH", str(cfg), raising=False)

    username = "alice"
    password_hash = "sha256:deadbeef"

    webui.save_user_config(username, password_hash)

    assert cfg.exists()
    data = yaml.safe_load(cfg.read_text())
    assert data["username"] == username
    assert data["password_hash"] == password_hash
