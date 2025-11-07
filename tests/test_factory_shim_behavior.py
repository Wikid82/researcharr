import importlib
import sys
import types


def test_shim_sets_impl_none_when_top_level_import_fails(monkeypatch):
    """Simulate importlib.import_module('factory') raising so the shim sets _impl = None."""
    # Ensure the package shim is not cached so import re-evaluates
    monkeypatch.delitem(sys.modules, "researcharr.factory", raising=False)

    orig_import = importlib.import_module

    def _raise_for_factory(name, package=None):
        if name == "factory":
            raise ImportError("simulated import failure")
        return orig_import(name, package=package)

    monkeypatch.setattr(importlib, "import_module", _raise_for_factory)

    # Import the shim; it should catch the ImportError and set _impl = None
    shim = importlib.import_module("researcharr.factory")
    assert hasattr(shim, "_impl")
    assert shim._impl is None


def test_shim_reexports_public_names_from_top_level_module(monkeypatch):
    """When a top-level `factory` module is present, the shim should re-export its public names."""
    # Prepare a fake top-level module with a couple of public symbols
    mod = types.ModuleType("factory")

    def create_app_marker():
        return "created"

    mod.create_app = create_app_marker
    mod.SOME_CONST = 12345

    # Ensure importlib.import_module will return our fake module
    orig_import = importlib.import_module

    def _fake_import(name, package=None):
        if name == "factory":
            return mod
        return orig_import(name, package=package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)
    # Make sure our fake module is also present in sys.modules for other import paths
    monkeypatch.setitem(sys.modules, "factory", mod)

    # Remove any cached shim so re-loading the shim file picks up the fake top-level module
    monkeypatch.delitem(sys.modules, "researcharr.factory", raising=False)

    # Load the package shim file directly so import order and package __path__ do
    # not cause Python to bind the wrong module name (we want to execute the
    # shim source under our controlled import hooks).
    import os
    from importlib import util

    shim_path = os.path.join(os.path.dirname(__file__), "..", "researcharr", "factory.py")
    shim_path = os.path.abspath(shim_path)
    spec = util.spec_from_file_location("researcharr.factory_shim_test", shim_path)
    shim = util.module_from_spec(spec)
    spec.loader.exec_module(shim)

    assert hasattr(shim, "_impl")
    assert shim._impl is mod
    # Public names from the top-level module should be available on the shim
    assert hasattr(shim, "create_app")
    assert shim.create_app is create_app_marker
    assert getattr(shim, "SOME_CONST") == 12345
