# 'os' not required in this test


def test_env_bool_truthy_and_falsy(monkeypatch):
    import importlib

    import researcharr.webui as webui

    importlib.reload(webui)

    monkeypatch.setenv("WEBUI_DEV_PRINT_CREDS", "true")
    importlib.reload(webui)
    assert webui._env_bool("WEBUI_DEV_PRINT_CREDS") is True

    monkeypatch.setenv("WEBUI_DEV_PRINT_CREDS", "0")
    importlib.reload(webui)
    assert webui._env_bool("WEBUI_DEV_PRINT_CREDS") is False
