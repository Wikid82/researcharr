"""Tests covering package initialization behaviors."""

import importlib
import sys
import types
import pytest


def test_package_import_and_basic_attributes():
    pkg = importlib.import_module("researcharr")
    # Version exposed
    assert hasattr(pkg, "__version__")
    # sqlite3 should be available on the package
    assert hasattr(pkg, "sqlite3")
    assert "researcharr.sqlite3" in sys.modules
    # __path__ should be a list with at least two entries
    p = getattr(pkg, "__path__", [])
    assert isinstance(p, list) and len(p) >= 2


def test_package_exposes_backups_submodule():
    # Import via package-qualified name to exercise lazy resolution
    mod = importlib.import_module("researcharr.backups")
    assert hasattr(mod, "create_backup_file")
    assert hasattr(mod, "prune_backups")


def test_factory_delegate_present_and_callable():
    pkg = importlib.import_module("researcharr")
    fac = getattr(pkg, "factory", None)
    assert fac is not None
    assert hasattr(fac, "create_app")
    assert callable(fac.create_app)
    # Delegate may succeed (return app) or raise ImportError when no impl.
    try:
        app = fac.create_app()
        # If it returns, assert minimal Flask-like interface
        assert hasattr(app, "test_client")
    except ImportError:
        pass
