import time


class FakeRegistry:
    def __init__(self, instance=None, raise_on_create=False):
        self._instance = instance
        self._raise = raise_on_create

    def get(self, name):
        # Non-None indicates the plugin exists
        return object()

    def create_instance(self, name, cfg):
        if self._raise:
            raise Exception("create-instance-failed")
        return self._instance


class ValidateFalse:
    def validate(self):
        return False


class ValidateRaise:
    def validate(self):
        raise Exception("validate-failed")


class SyncFalse:
    def sync(self):
        return False


class SyncRaise:
    def sync(self):
        raise Exception("sync-failed")


def test_api_plugin_validate_invalid_index(client, login, app):
    login()
    # registry reports plugin exists but no instances configured
    app.plugin_registry = FakeRegistry(instance=ValidateFalse())
    app.config_data["foo"] = []
    rv = client.post("/api/plugins/foo/validate/0")
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get("error") == "invalid_instance"


def test_api_plugin_validate_falsy_and_metrics(client, login, app):
    login()
    app.plugin_registry = FakeRegistry(instance=ValidateFalse())
    app.config_data["foo"] = [{"enabled": True, "url": "http://x", "api_key": "k"}]
    # Ensure metrics bucket absent to exercise creation path
    app.metrics.pop("plugins", None)
    app.metrics["plugins"] = {}
    rv = client.post("/api/plugins/foo/validate/0")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("result") is False
    # metrics should record the attempt and error
    pm = app.metrics.get("plugins", {}).get("foo")
    assert pm is not None
    assert pm.get("validate_attempts", 0) >= 1
    assert pm.get("validate_errors", 0) >= 1


def test_api_plugin_validate_exception(client, login, app):
    login()
    # create_instance raises
    app.plugin_registry = FakeRegistry(instance=None, raise_on_create=True)
    app.config_data["foo"] = [{"enabled": True, "url": "http://x", "api_key": "k"}]
    rv = client.post("/api/plugins/foo/validate/0")
    assert rv.status_code == 500
    data = rv.get_json()
    assert data.get("error") == "validate_failed"


def test_api_plugin_sync_falsy_and_exception(client, login, app):
    login()
    # falsy sync
    app.plugin_registry = FakeRegistry(instance=SyncFalse())
    app.config_data["bar"] = [{"enabled": True, "url": "http://x", "api_key": "k"}]
    rv = client.post("/api/plugins/bar/sync/0")
    assert rv.status_code == 200
    assert rv.get_json().get("result") is False

    # exception during create_instance
    app.plugin_registry = FakeRegistry(instance=None, raise_on_create=True)
    app.config_data["bar"] = [{"enabled": True, "url": "http://x", "api_key": "k"}]
    rv2 = client.post("/api/plugins/bar/sync/0")
    assert rv2.status_code == 500
    assert rv2.get_json().get("error") == "sync_failed"


def test_api_status_plugins_summary_rates(client, login, app):
    login()
    # seed metrics with known values
    app.metrics["plugins"] = {
        "p1": {
            "validate_attempts": 2,
            "validate_errors": 1,
            "sync_attempts": 4,
            "sync_errors": 1,
            "last_error": int(time.time()),
            "last_error_msg": "boom",
        }
    }
    rv = client.get("/api/status")
    assert rv.status_code == 200
    data = rv.get_json()
    plugins = data.get("plugins") or {}
    p1 = plugins.get("p1")
    assert p1 is not None
    # validate_error_rate = 1 / 2 * 100 = 50.0
    assert p1.get("validate_error_rate") == 50.0
    # sync_error_rate = 1 / 4 * 100 = 25.0
    assert p1.get("sync_error_rate") == 25.0
