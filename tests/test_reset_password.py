import os

import pytest
import yaml

from researcharr import webui
from researcharr.factory import create_app


def test_reset_password_updates_config(tmp_path, monkeypatch):
    # Prepare a temp user config path so we don't touch repo files
    user_cfg = tmp_path / "webui_user.yml"
    monkeypatch.setenv("WEBUI_RESET_TOKEN", "secrettoken")
    # Ensure webui.save_user_config writes to our temp path
    monkeypatch.setattr(webui, "USER_CONFIG_PATH", str(user_cfg), raising=False)

    app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()

    # Ensure initial user is the default from create_app
    assert app.config_data["user"]["username"] == "admin"

    # Post reset with correct token and matching passwords
    rv = client.post(
        "/reset-password",
        data={
            "username": "researcharr",
            "token": "secrettoken",
            "password": "newstrongpass",
            "confirm": "newstrongpass",
        },
        follow_redirects=True,
    )

    # After reset, the in-memory config should be updated
    assert app.config_data["user"]["username"] == "researcharr"
    assert app.config_data["user"]["password"] == "newstrongpass"

    # And the user config file should exist and contain a password_hash
    assert user_cfg.exists()
    data = yaml.safe_load(user_cfg.read_text())
    assert data.get("username") == "researcharr"
    assert "password_hash" in data
