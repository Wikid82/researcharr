import sys

import pytest

import researcharr.factory as factory


def test_create_app_smoke():
    app = factory.create_app()
    from flask import Flask

    assert isinstance(app, Flask)
    # basic runtime structures
    assert "config_data" in app.__dict__
    assert "metrics" in app.__dict__


def test_create_app_requires_secret_in_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    # In production mode without SECRET_KEY create_app should exit
    with pytest.raises(SystemExit):
        factory.create_app()


def test_create_app_uses_webui_load_and_migrates_api_key(monkeypatch):
    # Provide a fake top-level `webui` module that returns a legacy api_key
    mod = type(sys)("webui")

    def load_user_config():
        return {"api_key": "plain-token"}

    def save_user_config(*args, **kwargs):
        # record was called by being present; no-op
        return None

    mod.load_user_config = load_user_config
    mod.save_user_config = save_user_config
    monkeypatch.setitem(sys.modules, "webui", mod)

    # Create app and ensure an api_key_hash exists in config_data
    app = factory.create_app()
    assert "api_key_hash" in app.config_data.get("general", {})


def test_create_app_attaches_plugin_registry():
    app = factory.create_app()
    # plugin registry should be attached even if no plugins are discovered
    assert hasattr(app, "plugin_registry")
    reg = getattr(app, "plugin_registry")
    assert hasattr(reg, "list_plugins")
    assert callable(reg.list_plugins)
