import importlib
import sys
import types


def _make_fake_flask():
    fake_flask = types.ModuleType("flask")
    for name in (
        "Flask",
        "Response",
        "flash",
        "jsonify",
        "redirect",
        "render_template",
        "request",
        "send_file",
        "session",
        "stream_with_context",
        "url_for",
    ):
        setattr(fake_flask, name, object())
    return fake_flask


def test_factory_shim_reexports_top_level_factory(monkeypatch):
    # Create a dummy top-level 'factory' module with a marker function
    mod = types.ModuleType("factory")

    def create_app_marker():
        return "created"

    mod.create_app = create_app_marker
    # Install into sys.modules so importlib.import_module('factory') finds it
    monkeypatch.setitem(sys.modules, "factory", mod)

    # Ensure any importlib.import_module('factory') call returns our dummy
    orig_import_module = importlib.import_module

    def _fake_import(name, package=None):
        if name == "factory":
            return mod
        return orig_import_module(name, package=package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    # Provide a minimal fake `flask` module so importing the shim doesn't fail
    fake_flask = _make_fake_flask()
    monkeypatch.setitem(sys.modules, "flask", fake_flask)

    # Ensure any previous import of the package shim is removed so our
    # monkeypatch of importlib.import_module is used when the shim runs.
    monkeypatch.delitem(sys.modules, "researcharr.factory", raising=False)

    # Load the package shim source as an isolated module so we can control
    # how it resolves the top-level `factory` import without relying on
    # import caching performed by the test runner.
    import os
    from importlib import util

    shim_path = os.path.join(os.path.dirname(__file__), "..", "researcharr", "factory.py")
    shim_path = os.path.abspath(shim_path)
    spec = util.spec_from_file_location("researcharr.factory_shim_test", shim_path)
    shim = util.module_from_spec(spec)
    spec.loader.exec_module(shim)

    try:
        assert hasattr(shim, "_impl")
        # Shim should reference the injected module
        assert shim._impl is mod
        # The shim should re-export the create_app symbol from the top-level module
        assert hasattr(shim, "create_app")
        assert shim.create_app is create_app_marker
    finally:
        # cleanup: restore importlib and remove our dummy module and reload shim
        monkeypatch.setattr(importlib, "import_module", orig_import_module)
        monkeypatch.delitem(sys.modules, "factory", raising=False)
        monkeypatch.delitem(sys.modules, "flask", raising=False)
        # shim was loaded as an isolated module and may not be present in
        # sys.modules under its spec name; no reload required.


def test_factory_shim_absent_top_level(monkeypatch):
    # Ensure no top-level 'factory' is present
    monkeypatch.delitem(sys.modules, "factory", raising=False)

    # Provide a minimal fake `flask` module so importing the shim doesn't fail
    fake_flask = _make_fake_flask()
    monkeypatch.setitem(sys.modules, "flask", fake_flask)

    # Ensure any previous import of the package shim is removed so our
    # fake flask is seen when the shim re-evaluates importlib.import_module.
    monkeypatch.delitem(sys.modules, "researcharr.factory", raising=False)

    import os
    from importlib import util

    shim_path = os.path.join(os.path.dirname(__file__), "..", "researcharr", "factory.py")
    shim_path = os.path.abspath(shim_path)
    spec = util.spec_from_file_location("researcharr.factory_shim_test", shim_path)
    shim = util.module_from_spec(spec)
    spec.loader.exec_module(shim)

    # When top-level implementation is absent, _impl should be present but None
    assert hasattr(shim, "_impl")
    assert shim._impl is None
    # And common names should not be bound to the shim (create_app may be absent)
    # We assert that either create_app is not present or if present it's a callable.
    if hasattr(shim, "create_app"):
        assert callable(shim.create_app)
