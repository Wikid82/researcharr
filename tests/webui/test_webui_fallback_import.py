import importlib
import importlib.util
import sys
from unittest.mock import patch


def test_webui_fallback_file_loader(monkeypatch):
    # Remove any existing top-level webui to force fallback path
    sys.modules.pop("webui", None)
    # Cause importlib.import_module("webui") to fail
    real_import = importlib.import_module

    def side_effect(name, *a, **k):
        if name == "webui":
            raise ImportError()
        return real_import(name, *a, **k)

    with patch("importlib.import_module", side_effect=side_effect):
        mod = importlib.import_module("researcharr.webui")
    # Verify shim exports
    assert hasattr(mod, "_env_bool")
    assert hasattr(mod, "load_user_config")
    assert hasattr(mod, "save_user_config")
