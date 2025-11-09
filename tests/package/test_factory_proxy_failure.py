"""Tests for factory proxy failure paths and delegate installation."""

import importlib
import sys
import pytest


def test_factory_proxy_placeholder_raises():
    # Import package to ensure proxies installed
    pkg = importlib.import_module("researcharr")
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


def test_factory_delegate_invocation_without_impl_raises_importerror_or_handles():
    """Delegate may return app or raise ImportError depending on environment.

    In environments where a real factory implementation exists, create_app may
    succeed. Where none exists it should raise ImportError. Accept both to keep
    test stable across dev setups.
    """
    pkg = importlib.import_module("researcharr")
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
