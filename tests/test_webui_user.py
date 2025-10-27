import os
import yaml
import importlib


def test_first_run_creates_user_config(tmp_path, monkeypatch):
    # point USER_CONFIG_PATH to tmp location via researcharr.researcharr symbol
    monkeypatch.setattr(
        "researcharr.researcharr.USER_CONFIG_PATH", str(tmp_path / "webui_user.yml"),
        raising=False,
    )
    # reload webui to pick up patched USER_CONFIG_PATH
    import researcharr.webui as webui

    importlib.reload(webui)

    # ensure file does not exist
    p = tmp_path / "webui_user.yml"
    if p.exists():
        p.unlink()

    data = webui.load_user_config()
    # returned data must include plaintext password and api_key on first run
    assert "password" in data and data["password"]
    assert "api_key" in data and data["api_key"]

    # persisted file must exist and should not contain plaintext keys
    assert p.exists()
    persisted = yaml.safe_load(p.read_text())
    assert "password_hash" in persisted
    assert "api_key_hash" in persisted
    assert "password" not in persisted
    assert "api_key" not in persisted


def test_save_user_config_writes_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "researcharr.researcharr.USER_CONFIG_PATH", str(tmp_path / "webui_user.yml"),
        raising=False,
    )
    import researcharr.webui as webui
    importlib.reload(webui)

    p = tmp_path / "webui_user.yml"
    if p.exists():
        p.unlink()

    # call save with an api_key; function will hash it
    webui.save_user_config("bob", "pw-hash", api_key="secret-token")
    assert p.exists()
    data = yaml.safe_load(p.read_text())
    assert data.get("username") == "bob"
    assert "api_key_hash" in data and data["api_key_hash"]
