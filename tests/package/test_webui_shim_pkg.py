"""Tests for the `researcharr.webui` shim module."""

import importlib

import pytest


def test_webui_env_bool(monkeypatch):
    webui = importlib.import_module("researcharr.webui")
    monkeypatch.setenv("FEATURE_FLAG", "true")
    assert webui._env_bool("FEATURE_FLAG") is True
    monkeypatch.setenv("FEATURE_FLAG", "0")
    assert webui._env_bool("FEATURE_FLAG") is False


def test_webui_load_user_config_when_no_rdb():
    webui = importlib.import_module("researcharr.webui")
    # Ensure rdb unset
    if getattr(webui, "rdb", None) is not None:
        webui.rdb = None  # type: ignore
    assert webui.load_user_config() is None


def test_webui_load_user_config_with_rdb(monkeypatch):
    webui = importlib.import_module("researcharr.webui")
    data = {"username": "u", "password_hash": "p"}

    class DummyRDB:
        def load_user(self):  # noqa: D401
            return data

        def save_user(self, *a, **kw):  # noqa: D401
            pass

    webui.rdb = DummyRDB()  # type: ignore
    assert webui.load_user_config() == data


def test_webui_save_user_config_requires_rdb():
    webui = importlib.import_module("researcharr.webui")
    webui.rdb = None  # type: ignore
    with pytest.raises(RuntimeError):
        webui.save_user_config("user", "hash")


def test_webui_save_user_config_hashes_and_delegates(monkeypatch):
    webui = importlib.import_module("researcharr.webui")
    saved = {}

    class DummyRDB:
        def load_user(self):
            return None

        def save_user(self, username, password_hash, api_key_hash):  # noqa: D401
            saved.update(
                {
                    "username": username,
                    "password_hash": password_hash,
                    "api_key_hash": api_key_hash,
                }
            )

    webui.rdb = DummyRDB()  # type: ignore
    # `detect-secrets` can flag the literal string below as a false positive.
    # Allowlist the instance here so pre-commit doesn't fail on test data.
    # Use a clearly non-secret test value so detect-secrets won't flag this test.
    result = webui.save_user_config("user", "dummy_pw_hash", api_key="example_test_api_key")
    # Password hash is passed through unchanged, api key is hashed (prefix 'scrypt' typical)
    assert result["username"] == "user"
    assert result["password_hash"] == "dummy_pw_hash"
    assert result["api_key_hash"].startswith("scrypt")
    assert saved["username"] == "user"
    assert saved["api_key_hash"].startswith("scrypt")
