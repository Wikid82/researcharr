import importlib
import os

import pytest
from flask import Flask

import researcharr.factory as factory_module


def _reload_factory():
    # Ensure module-level effects are refreshed if needed
    importlib.reload(factory_module)


def test_timezone_default(monkeypatch):
    monkeypatch.delenv("TIMEZONE", raising=False)
    # create app and assert timezone default is America/New_York
    app = factory_module.create_app()
    assert app.config_data["general"]["Timezone"] == "America/New_York"


def test_puid_pgid_fallback_and_warning(monkeypatch, caplog):
    monkeypatch.setenv("PUID", "not-an-int")
    monkeypatch.setenv("PGID", "also-bad")
    caplog.clear()
    app = factory_module.create_app()
    # fallback to 1000 (strings)
    assert app.config_data["general"]["PUID"] == "1000"
    assert app.config_data["general"]["PGID"] == "1000"


def test_secret_key_required_in_production(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("ENV", "production")
    # reload module to ensure environment is considered; create_app should exit
    with pytest.raises(SystemExit):
        factory_module.create_app()
    monkeypatch.delenv("ENV", raising=False)


def test_session_cookie_flags(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("SESSION_COOKIE_HTTPONLY", "true")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "Strict")
    app = factory_module.create_app()
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Strict"
