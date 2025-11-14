import importlib
import sys

from werkzeug.security import generate_password_hash


def _reload_pkg_webui():
    if "researcharr.webui" in sys.modules:
        sys.modules.pop("researcharr.webui")
    return importlib.import_module("researcharr.webui")


def test_env_bool_truthy_values_pkg(monkeypatch):
    w = _reload_pkg_webui()
    for val in ["1", "true", "TRUE", "yes", "YeS"]:
        monkeypatch.setenv("TEST_BOOL", val)
        assert w._env_bool("TEST_BOOL") is True


def test_env_bool_default_false_pkg(monkeypatch):
    w = _reload_pkg_webui()
    monkeypatch.delenv("UNSET_BOOL", raising=False)
    assert w._env_bool("UNSET_BOOL") is False


def test_pkg_load_user_config_none_backend(monkeypatch):
    w = _reload_pkg_webui()
    w.rdb = None
    assert w.load_user_config() is None


def test_pkg_load_user_config_success(monkeypatch):
    w = _reload_pkg_webui()

    class FakeDB:
        def load_user(self):
            return {"username": "alice", "password_hash": "ph", "api_key_hash": "akh"}

    w.rdb = FakeDB()
    assert w.load_user_config() == {
        "username": "alice",
        "password_hash": "ph",
        "api_key_hash": "akh",
    }


def test_pkg_save_user_config_no_backend_raises():
    w = _reload_pkg_webui()
    w.rdb = None
    try:
        w.save_user_config("alice", "ph")
    except RuntimeError as e:
        assert "DB backend" in str(e)
    else:  # pragma: no cover - defensive
        assert False, "Expected RuntimeError"


def test_pkg_save_user_config_hashes_api_key(monkeypatch):
    w = _reload_pkg_webui()

    captured = {}

    class FakeDB:
        def save_user(self, username, password_hash, api_key_hash):
            captured.update(
                {
                    "username": username,
                    "password_hash": password_hash,
                    "api_key_hash": api_key_hash,
                }
            )

    w.rdb = FakeDB()
    pw_hash = generate_password_hash("secret")
    result = w.save_user_config("alice", pw_hash, api_key="radarr123")
    assert captured["api_key_hash"] != "radarr123"
    assert captured["api_key_hash"] == result["api_key_hash"]
    assert result["username"] == "alice"
    assert result["password_hash"] == pw_hash


def test_pkg_save_user_config_preserves_api_key_hash(monkeypatch):
    w = _reload_pkg_webui()

    captured = {}

    class FakeDB:
        def save_user(self, username, password_hash, api_key_hash):
            captured.update(
                {
                    "username": username,
                    "password_hash": password_hash,
                    "api_key_hash": api_key_hash,
                }
            )

    w.rdb = FakeDB()
    pw_hash = generate_password_hash("secret")
    existing_api_hash = generate_password_hash("api-key")
    result = w.save_user_config("bob", pw_hash, api_key_hash=existing_api_hash)
    assert captured["api_key_hash"] == existing_api_hash
    assert result["api_key_hash"] == existing_api_hash
    assert result["username"] == "bob"
