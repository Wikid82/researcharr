import importlib
import sys
from unittest.mock import patch


def test_registry_local_fallback_when_top_level_missing(monkeypatch):
    # Ensure top-level plugins.registry cannot be imported
    sys.modules.pop("plugins", None)

    real_import = importlib.import_module

    def import_side_effect(name, *a, **k):
        if name == "plugins.registry":
            raise ImportError()
        return real_import(name, *a, **k)

    with patch("importlib.import_module", side_effect=import_side_effect):
        mod = importlib.import_module("researcharr.plugins.registry")
        # Use the locally defined fallback class
        PR = mod.PluginRegistry
        reg = PR()
        reg.register("x", dict)
        assert reg.get("x") is dict
        assert "x" in reg.list_plugins()
