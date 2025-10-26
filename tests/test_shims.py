import importlib
import sys
from types import ModuleType


def test_shim_fallback_to_package(monkeypatch):
    """If the file-based loader can't find a top-level file, the package
    shim should fall back to package-style import if available.
    """
    # Ensure the file-based checks fail by forcing os.path.isfile -> False
    monkeypatch.setattr("os.path.isfile", lambda p: False)

    # Insert a dummy implementation module into sys.modules so the package
    # style import can succeed even though no file exists on disk.
    dummy = ModuleType("researcharr.researcharr")
    # provide the minimal public symbols the shim checks for
    dummy.init_db = lambda *a, **k: None
    dummy.create_metrics_app = lambda *a, **k: None
    sys.modules["researcharr.researcharr"] = dummy

    # Reload the package shim to exercise the fallback branch
    pkg = importlib.import_module("researcharr")
    importlib.reload(pkg)

    # After reload, the package should expose the researcharr attribute
    assert hasattr(pkg, "researcharr")
    impl = getattr(pkg, "researcharr")
    assert hasattr(impl, "init_db")
    assert hasattr(impl, "create_metrics_app")


def test_shim_exposes_requests_and_yaml(monkeypatch):
    """When the implementation is loaded by path the shim ensures common
    top-level modules (requests, yaml) are available as attributes on the
    loaded module so tests can monkeypatch them.
    """
    # Create lightweight fake modules and insert into sys.modules so the
    # shim import will find them and copy them onto the implementation.
    fake_requests = ModuleType("requests")
    fake_yaml = ModuleType("yaml")
    sys.modules.setdefault("requests", fake_requests)
    sys.modules.setdefault("yaml", fake_yaml)

    # Reload the package to force re-evaluation of the shim loading logic.
    pkg = importlib.import_module("researcharr")
    importlib.reload(pkg)

    impl = getattr(pkg, "researcharr")
    # The shim should expose these modules on the implementation module
    assert hasattr(impl, "requests")
    assert hasattr(impl, "yaml")
