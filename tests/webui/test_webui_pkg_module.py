import importlib.util
import os
import sys


def _load_pkg_webui():
    pkg = importlib.import_module("researcharr")
    path = os.path.join(os.path.dirname(pkg.__file__), "webui.py")
    sys.modules.pop("researcharr.webui", None)
    spec = importlib.util.spec_from_file_location("researcharr.webui", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    sys.modules["researcharr.webui"] = mod
    return mod


def test_pkg_webui_exports_and_env_bool(monkeypatch):
    webui = _load_pkg_webui()
    monkeypatch.setenv("WBOOL", "yes")
    assert hasattr(webui, "_env_bool")
    assert webui._env_bool("WBOOL") is True
    assert hasattr(webui, "load_user_config")
    assert hasattr(webui, "save_user_config")
