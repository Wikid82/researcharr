import os

import pytest

import factory as top_factory


@pytest.fixture(scope="function")
def app_with_override(monkeypatch):
    # Ensure override applied before app/client fixture construction
    class _DummyWebUI:
        def load_user_config(self):  # pragma: no cover - simple stub
            return {}

        def save_user_config(self, *args, **kwargs):  # pragma: no cover - simple stub
            # accept username, password_hash, and optional api_key/api_key_hash
            self._saved = {"args": args, "kwargs": kwargs}

    top_factory._RuntimeConfig.set_webui(_DummyWebUI())
    os.environ["FACTORY_DEBUG_SETUP"] = "1"
    yield
    # cleanup
    top_factory._RuntimeConfig.clear_webui()
    os.environ.pop("FACTORY_DEBUG_SETUP", None)


def test_setup_route_sets_flag(app_with_override, client):
    # Ensure override is active before client app creation; post to /setup form
    resp = client.post(
        "/setup",
        data={"username": "u", "password": "longpassword", "confirm": "longpassword"},
        follow_redirects=False,
    )
    # On success with generated API token, route renders a template (200)
    assert resp.status_code in (200, 302)
    assert client.application.config.get("USER_CONFIG_EXISTS") is True
