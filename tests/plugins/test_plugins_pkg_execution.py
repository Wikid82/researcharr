import importlib
import sys
from unittest.mock import patch


def test_plugins_pkg_import_reexports(monkeypatch):
    # Ensure a real import path is used; module should expose attributes (object or module)
    mod = importlib.import_module("researcharr.plugins")
    for name in ["registry", "base", "clients", "media", "notifications", "scrapers"]:
        assert hasattr(mod, name)


def test_plugins_pkg_import_failure(monkeypatch):
    # Simulate failure importing top-level plugins; still import researcharr.plugins
    sys.modules.pop("plugins", None)
    real_import = importlib.import_module

    def side_effect(name, *a, **k):
        if name == "plugins":
            raise ImportError()
        return real_import(name, *a, **k)

    with patch("importlib.import_module", side_effect=side_effect):
        mod = importlib.import_module("researcharr.plugins")
    for name in ["registry", "base", "clients", "media", "notifications", "scrapers"]:
        assert hasattr(mod, name)
