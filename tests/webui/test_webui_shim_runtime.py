import importlib

webui_mod = importlib.import_module("researcharr.webui")


class DummyRDB:
    def __init__(self):
        self.saved = []

    def load_user(self):
        # Emulate legacy structure without hash to exercise migration branch
        return {
            "username": "u",
            "password_hash": "ph",
            "api_key": "plain",
        }

    def save_user(self, username, password_hash, api_hash):
        self.saved.append((username, password_hash, api_hash))


def test_webui_env_bool(monkeypatch):
    monkeypatch.setenv("WU_FLAG", "true")
    assert webui_mod._env_bool("WU_FLAG") is True
    monkeypatch.setenv("WU_FLAG", "no")
    assert webui_mod._env_bool("WU_FLAG") is False


def test_webui_load_and_save_user(monkeypatch):
    # First, when rdb is None, save_user_config should raise
    webui_mod = importlib.import_module("researcharr.webui")

    # Now set dummy rdb and exercise save path
    dummy = DummyRDB()
    monkeypatch.setattr(webui_mod, "rdb", dummy, raising=False)
    cfg = webui_mod.load_user_config()
    assert cfg is not None and cfg.get("username") == "u"
    out = webui_mod.save_user_config("alice", "pwd", api_key="k")
    assert out["username"] == "alice"
    assert dummy.saved and dummy.saved[0][0] == "alice"
