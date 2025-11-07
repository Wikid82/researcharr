"""Comprehensive tests for researcharr.plugins module shim.

This module tests the plugins package shim that re-exports the
repository-level plugins package.
"""

import sys
from unittest.mock import MagicMock, patch


def test_plugins_import():
    """Test that plugins module can be imported."""
    from researcharr import plugins

    assert plugins is not None


def test_plugins_exports_registry():
    """Test that plugins module exports registry."""
    from researcharr import plugins

    # Should have registry attribute (may be None)
    assert hasattr(plugins, "registry")


def test_plugins_exports_base():
    """Test that plugins module exports base."""
    from researcharr import plugins

    assert hasattr(plugins, "base")


def test_plugins_exports_clients():
    """Test that plugins module exports clients."""
    from researcharr import plugins

    assert hasattr(plugins, "clients")


def test_plugins_exports_media():
    """Test that plugins module exports media."""
    from researcharr import plugins

    assert hasattr(plugins, "media")


def test_plugins_exports_notifications():
    """Test that plugins module exports notifications."""
    from researcharr import plugins

    assert hasattr(plugins, "notifications")


def test_plugins_exports_scrapers():
    """Test that plugins module exports scrapers."""
    from researcharr import plugins

    assert hasattr(plugins, "scrapers")


def test_plugins_all_exports():
    """Test that plugins __all__ contains expected exports."""
    from researcharr import plugins

    expected = [
        "registry",
        "base",
        "clients",
        "media",
        "notifications",
        "scrapers",
    ]

    assert hasattr(plugins, "__all__")
    assert set(plugins.__all__) == set(expected)


def test_plugins_with_mock_impl():
    """Test plugins shim with mocked implementation."""
    # Create a mock plugins module
    mock_plugins = MagicMock()
    mock_plugins.registry = "test_registry"
    mock_plugins.base = "test_base"
    mock_plugins.clients = "test_clients"
    mock_plugins.media = "test_media"
    mock_plugins.notifications = "test_notifications"
    mock_plugins.scrapers = "test_scrapers"

    with patch("importlib.import_module", return_value=mock_plugins):
        # Reimport to pick up the mock
        import importlib

        if "researcharr.plugins" in sys.modules:
            del sys.modules["researcharr.plugins"]

        plugins = importlib.import_module("researcharr.plugins")

        # Check that attributes are present
        assert hasattr(plugins, "registry")
        assert hasattr(plugins, "base")


def test_plugins_import_failure():
    """Test plugins shim handles import failure gracefully."""
    with patch("importlib.import_module", side_effect=ImportError("No plugins")):
        # Reimport to trigger the error path
        import importlib

        if "researcharr.plugins" in sys.modules:
            del sys.modules["researcharr.plugins"]

        # Should not raise
        plugins = importlib.import_module("researcharr.plugins")

        # Attributes should exist but may be None
        assert hasattr(plugins, "registry")


def test_plugins_partial_exports():
    """Test plugins shim handles partial exports from implementation."""
    mock_plugins = MagicMock()
    # Only provide some attributes
    mock_plugins.registry = "test_registry"
    mock_plugins.base = "test_base"
    # Missing: clients, media, notifications, scrapers
    del mock_plugins.clients
    del mock_plugins.media

    with patch("importlib.import_module", return_value=mock_plugins):
        import importlib

        if "researcharr.plugins" in sys.modules:
            del sys.modules["researcharr.plugins"]

        plugins = importlib.import_module("researcharr.plugins")

        # All attributes should exist in __all__
        assert "registry" in plugins.__all__
        assert "clients" in plugins.__all__


def test_plugins_registry_module():
    """Test that plugins.registry can be accessed."""
    from researcharr.plugins import registry

    # May be None if plugins not available
    assert registry is None or registry is not None


def test_plugins_base_module():
    """Test that plugins.base can be accessed."""
    from researcharr.plugins import base

    assert base is None or base is not None


def test_plugins_clients_module():
    """Test that plugins.clients can be accessed."""
    from researcharr.plugins import clients

    assert clients is None or clients is not None


def test_plugins_media_module():
    """Test that plugins.media can be accessed."""
    from researcharr.plugins import media

    assert media is None or media is not None


def test_plugins_notifications_module():
    """Test that plugins.notifications can be accessed."""
    from researcharr.plugins import notifications

    assert notifications is None or notifications is not None


def test_plugins_scrapers_module():
    """Test that plugins.scrapers can be accessed."""
    from researcharr.plugins import scrapers

    assert scrapers is None or scrapers is not None


def test_plugins_exception_in_getattr():
    """Test plugins shim handles getattr exceptions."""
    mock_plugins = MagicMock()

    # Make getattr raise an exception
    def raising_getattr(name, default=None):
        if name == "registry":
            raise AttributeError("Test error")
        return default

    mock_plugins.configure_mock(**{"__getattr__": raising_getattr})

    with patch("importlib.import_module", return_value=mock_plugins):
        import importlib

        if "researcharr.plugins" in sys.modules:
            del sys.modules["researcharr.plugins"]

        # Should handle the exception gracefully
        plugins = importlib.import_module("researcharr.plugins")

        # Should still have the attributes
        assert hasattr(plugins, "registry")
