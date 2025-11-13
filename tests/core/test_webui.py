import importlib
import sys

from werkzeug.security import generate_password_hash


def _reload_webui():
    # Ensure a clean module state between tests.
    if "webui" in sys.modules:
        sys.modules.pop("webui")
    return importlib.import_module("webui")


def test_env_bool_truthy_values(monkeypatch):
    webui = _reload_webui()
    for val in ["1", "true", "TRUE", "yes", "YeS"]:
        monkeypatch.setenv("TEST_BOOL", val)
        assert webui._env_bool("TEST_BOOL") is True


def test_env_bool_default_false(monkeypatch):
    webui = _reload_webui()
    monkeypatch.delenv("UNSET_BOOL", raising=False)
    assert webui._env_bool("UNSET_BOOL") is False


def test_load_user_config_none_backend(monkeypatch):
    webui = _reload_webui()
    # Force rdb None even if import succeeded.
    webui.rdb = None
    assert webui.load_user_config() is None


def test_load_user_config_success(monkeypatch):
    webui = _reload_webui()

    class FakeDB:
        def load_user(self):
            return {"username": "alice", "password_hash": "ph", "api_key_hash": "akh"}

    webui.rdb = FakeDB()
    assert webui.load_user_config() == {
        "username": "alice",
        "password_hash": "ph",
        "api_key_hash": "akh",
    }


def test_load_user_config_error(monkeypatch):
    webui = _reload_webui()

    class FakeDB:
        def load_user(self):  # pragma: no cover - exercised by exception path
            raise RuntimeError("boom")

    webui.rdb = FakeDB()
    assert webui.load_user_config() is None


def test_save_user_config_no_backend_raises():
    webui = _reload_webui()
    webui.rdb = None
    try:
        webui.save_user_config("alice", "ph")
    except RuntimeError as e:
        assert "DB backend" in str(e)
    else:  # pragma: no cover - defensive
        assert False, "Expected RuntimeError"


def test_save_user_config_hashes_api_key(monkeypatch):
    webui = _reload_webui()

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

    webui.rdb = FakeDB()
    pw_hash = generate_password_hash("secret")
    result = webui.save_user_config("alice", pw_hash, api_key="radarr123")
    # Ensure save_user called with hashed api key (cannot predict exact hash, but ensure differs & non-empty)
    assert captured["api_key_hash"] != "radarr123"
    assert captured["api_key_hash"] == result["api_key_hash"]
    assert result["username"] == "alice"
    assert result["password_hash"] == pw_hash


def test_save_user_config_preserves_api_key_hash(monkeypatch):
    webui = _reload_webui()

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

    webui.rdb = FakeDB()
    pw_hash = generate_password_hash("secret")
    existing_api_hash = generate_password_hash("api-key")
    result = webui.save_user_config("bob", pw_hash, api_key_hash=existing_api_hash)
    assert captured["api_key_hash"] == existing_api_hash
    assert result["api_key_hash"] == existing_api_hash
    assert result["username"] == "bob"
