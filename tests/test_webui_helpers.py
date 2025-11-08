import types

import pytest

# Import from researcharr package to ensure consistent module identity
import researcharr.webui as webui


def test_env_bool_truthy_and_falsey(monkeypatch):
    monkeypatch.setenv("SOME_FLAG", "true")
    assert webui._env_bool("SOME_FLAG") is True
    monkeypatch.setenv("SOME_FLAG", "1")
    assert webui._env_bool("SOME_FLAG") is True
    monkeypatch.setenv("SOME_FLAG", "no")
    assert webui._env_bool("SOME_FLAG") is False


def test_load_user_config_no_db(monkeypatch):
    # Ensure rdb is None - patch all module references
    import sys

    # Patch the function's module
    func_module = sys.modules[webui.load_user_config.__module__]
    monkeypatch.setattr(func_module, "rdb", None)
    # Also patch sys.modules['webui'] if it exists and is different
    if "webui" in sys.modules and sys.modules["webui"] is not func_module:
        monkeypatch.setattr(sys.modules["webui"], "rdb", None)
    # And patch the webui we imported
    monkeypatch.setattr(webui, "rdb", None)
    assert webui.load_user_config() is None


def test_load_user_config_with_db(monkeypatch):
    fake_db = types.SimpleNamespace()
    fake_db.load_user = lambda: {"username": "admin", "password_hash": "h"}
    monkeypatch.setattr(webui, "rdb", fake_db)
    res = webui.load_user_config()
    assert isinstance(res, dict)
    assert res["username"] == "admin"


def test_save_user_config_raises_without_db(monkeypatch):
    import sys

    # Patch all module references
    func_module = sys.modules[webui.save_user_config.__module__]
    monkeypatch.setattr(func_module, "rdb", None)
    if "webui" in sys.modules and sys.modules["webui"] is not func_module:
        monkeypatch.setattr(sys.modules["webui"], "rdb", None)
    monkeypatch.setattr(webui, "rdb", None)
    with pytest.raises(RuntimeError):
        webui.save_user_config("u", "phash")


def test_save_user_config_hashing_and_delegate(monkeypatch):
    calls = {}

    def fake_save_user(username, password_hash, api_hash):
        calls["username"] = username
        calls["password_hash"] = password_hash
        calls["api_hash"] = api_hash

    fake_db = types.SimpleNamespace()
    fake_db.save_user = fake_save_user
    import sys

    # Patch all module references
    func_module = sys.modules[webui.save_user_config.__module__]
    monkeypatch.setattr(func_module, "rdb", fake_db)
    if "webui" in sys.modules and sys.modules["webui"] is not func_module:
        monkeypatch.setattr(sys.modules["webui"], "rdb", fake_db)
    monkeypatch.setattr(webui, "rdb", fake_db)

    # provide api_key which should be hashed by save_user_config
    webui.save_user_config("bob", "pw_hash", api_key="secret")
    assert calls.get("username") == "bob"
    assert "password_hash" in calls
    assert calls["password_hash"] == "pw_hash"
    assert calls["api_hash"] is not None

    # provide api_key_hash directly
    calls.clear()
    webui.save_user_config("alice", "phash", api_key_hash="hashval")
    assert calls["username"] == "alice"
    assert calls["api_hash"] == "hashval"
