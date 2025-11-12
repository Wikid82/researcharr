"""Tests for factory proxy failure paths and delegate installation."""

import importlib
import sys

import pytest


def test_factory_proxy_placeholder_raises():
    # Import package to ensure proxies installed
    pkg = importlib.import_module("researcharr")
    # Snapshot existing modules and package helpers so we can restore after the test
    orig_top = sys.modules.get("factory")
    orig_pkg = sys.modules.get("researcharr.factory")
    _pkg_mod = importlib.import_module("researcharr")
    orig_delegate = getattr(_pkg_mod, "_create_app_delegate", None)
    orig_runtime = getattr(_pkg_mod, "_runtime_create_app", None)
    orig_impl_loaded = sys.modules.get("researcharr._factory_impl_loaded")
    try:
        # Force removal of any loaded real factory implementation to exercise placeholder
        sys.modules.pop("factory", None)
        sys.modules.pop("researcharr.factory", None)
        # Re-import proxies
        from researcharr._factory_proxy import create_proxies

        create_proxies()
        proxy = sys.modules.get("researcharr.factory")
        assert proxy is not None
        # Placeholder create_app should raise ImportError
        with pytest.raises(ImportError):
            proxy.create_app()  # type: ignore[attr-defined]
    finally:
        # Restore original module mappings to avoid polluting other tests
        try:
            if orig_top is None:
                sys.modules.pop("factory", None)
            else:
                sys.modules["factory"] = orig_top
        except Exception:
            pass
        try:
            if orig_pkg is None:
                sys.modules.pop("researcharr.factory", None)
            else:
                sys.modules["researcharr.factory"] = orig_pkg
                # restore package attribute if package loaded
                try:
                    _pkg = importlib.import_module("researcharr")
                    setattr(_pkg, "factory", orig_pkg)
                except Exception:
                    pass
        except Exception:
            pass
        # Restore any helpers installed onto the package module
        try:
            _pkg = importlib.import_module("researcharr")
            if orig_delegate is None:
                _pkg.__dict__.pop("_create_app_delegate", None)
            else:
                _pkg.__dict__["_create_app_delegate"] = orig_delegate
            if orig_runtime is None:
                _pkg.__dict__.pop("_runtime_create_app", None)
            else:
                _pkg.__dict__["_runtime_create_app"] = orig_runtime
        except Exception:
            pass
        try:
            if orig_impl_loaded is None:
                sys.modules.pop("researcharr._factory_impl_loaded", None)
            else:
                sys.modules["researcharr._factory_impl_loaded"] = orig_impl_loaded
        except Exception:
            pass


def test_factory_delegate_invocation_without_impl_raises_importerror_or_handles():
    """Delegate may return app or raise ImportError depending on environment.

    In environments where a real factory implementation exists, create_app may
    succeed. Where none exists it should raise ImportError. Accept both to keep
    test stable across dev setups.
    """
    pkg = importlib.import_module("researcharr")
    # Snapshot and restore to avoid leaking a mutated factory mapping
    orig_top = sys.modules.get("factory")
    orig_pkg = sys.modules.get("researcharr.factory")
    _pkg_mod = importlib.import_module("researcharr")
    orig_delegate = getattr(_pkg_mod, "_create_app_delegate", None)
    orig_runtime = getattr(_pkg_mod, "_runtime_create_app", None)
    orig_impl_loaded = sys.modules.get("researcharr._factory_impl_loaded")
    try:
        factory_mod = sys.modules.get("researcharr.factory") or getattr(pkg, "factory", None)
        assert factory_mod is not None
        assert hasattr(factory_mod, "create_app")
        try:
            result = factory_mod.create_app()  # type: ignore[attr-defined]
            # If it returns, ensure result has minimal Flask-like attributes
            assert hasattr(result, "test_client")
        except ImportError:
            # Accept ImportError path when no implementation present
            pass
    finally:
        try:
            if orig_top is None:
                sys.modules.pop("factory", None)
            else:
                sys.modules["factory"] = orig_top
        except Exception:
            pass
        try:
            if orig_pkg is None:
                sys.modules.pop("researcharr.factory", None)
            else:
                sys.modules["researcharr.factory"] = orig_pkg
                try:
                    _pkg = importlib.import_module("researcharr")
                    setattr(_pkg, "factory", orig_pkg)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            _pkg = importlib.import_module("researcharr")
            if orig_delegate is None:
                _pkg.__dict__.pop("_create_app_delegate", None)
            else:
                _pkg.__dict__["_create_app_delegate"] = orig_delegate
            if orig_runtime is None:
                _pkg.__dict__.pop("_runtime_create_app", None)
            else:
                _pkg.__dict__["_runtime_create_app"] = orig_runtime
        except Exception:
            pass
        try:
            if orig_impl_loaded is None:
                sys.modules.pop("researcharr._factory_impl_loaded", None)
            else:
                sys.modules["researcharr._factory_impl_loaded"] = orig_impl_loaded
        except Exception:
            pass
