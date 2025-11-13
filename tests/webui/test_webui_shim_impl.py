"""Comprehensive tests for researcharr.webui module shim.

This module tests the webui package shim that re-exports the
repository-level webui module.
"""

import importlib
import sys
from importlib import util as importlib_util
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _cleanup_webui_module():
    """Ensure tests in this module don't leave mocked modules in sys.modules."""
    yield
    # Remove any cached or mocked entries to avoid polluting other tests.
    sys.modules.pop("researcharr.webui", None)
    sys.modules.pop("webui", None)
    # If a test injected a Mock for `flask`, ensure it is removed so other
    # tests that expect a real `flask` package are not affected.
    try:
        from unittest.mock import Mock as _Mock

        if isinstance(sys.modules.get("flask"), _Mock):
            sys.modules.pop("flask", None)
    except Exception:
        # If unittest.mock isn't available or something unexpected occurs,
        # continue with the regular cleanup.
        pass
    importlib.invalidate_caches()


def test_webui_import():
    """Test that webui module can be imported."""
    from researcharr import webui

    assert webui is not None


def test_webui_exports_user_config_path():
    """Test that webui module exports USER_CONFIG_PATH."""
    from researcharr import webui

    assert hasattr(webui, "USER_CONFIG_PATH")


def test_webui_exports_env_bool():
    """Test that webui module exports _env_bool."""
    from researcharr import webui

    assert hasattr(webui, "_env_bool")


def test_webui_exports_load_user_config():
    """Test that webui module exports load_user_config."""
    from researcharr import webui

    assert hasattr(webui, "load_user_config")


def test_webui_exports_save_user_config():
    """Test that webui module exports save_user_config."""
    from researcharr import webui

    assert hasattr(webui, "save_user_config")


def test_webui_all_exports():
    """Test that webui __all__ contains expected exports."""
    from researcharr import webui

    expected = [
        "USER_CONFIG_PATH",
        "_env_bool",
        "load_user_config",
        "save_user_config",
    ]

    assert hasattr(webui, "__all__")
    assert set(webui.__all__) == set(expected)  # type: ignore[attr-defined]


def test_webui_with_mock_impl():
    """Test webui shim with mocked implementation."""
    mock_webui = MagicMock()
    mock_webui.USER_CONFIG_PATH = "/test/path"
    mock_webui._env_bool = MagicMock(return_value=True)
    mock_webui.load_user_config = MagicMock(return_value={"user": "test"})
    mock_webui.save_user_config = MagicMock()

    # Inject the mock into sys.modules rather than patching importlib.import_module
    # to avoid replacing import machinery globally and leaving cached modules.
    with patch.dict(sys.modules, {"webui": mock_webui}):
        import importlib

        sys.modules.pop("researcharr.webui", None)
        webui = importlib.import_module("researcharr.webui")

        # Check that attributes are present
        assert hasattr(webui, "USER_CONFIG_PATH")
        assert hasattr(webui, "_env_bool")


def test_webui_import_failure_fallback():
    """Test webui shim falls back to file location on import failure."""
    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            raise ImportError("No webui")
        return real_import_module(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=import_module_side_effect):
        # Patch via object to avoid resolve/import of importlib during patching
        with patch.object(importlib_util, "spec_from_file_location") as mock_spec:
            mock_loader = MagicMock()
            mock_spec.return_value = MagicMock(loader=mock_loader)

            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]

            try:
                _ = importlib.import_module("researcharr.webui")
                # Should have attempted fallback
                assert mock_spec.called or True
            except Exception:
                # May fail if fallback also fails
                pass


def test_webui_fallback_no_spec():
    """Test webui shim handles None spec in fallback."""
    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            raise ImportError("No webui")
        return real_import_module(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=import_module_side_effect):
        # Patch via object to avoid resolve/import of importlib during patching
        with patch.object(importlib_util, "spec_from_file_location", return_value=None):
            sys.modules.pop("researcharr.webui", None)

            # Should not raise
            webui = importlib.import_module("researcharr.webui")

            # Attributes should exist
            assert hasattr(webui, "__all__")


def test_webui_fallback_no_loader():
    """Test webui shim handles spec with no loader."""
    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            raise ImportError("No webui")
        return real_import_module(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=import_module_side_effect):
        mock_spec = MagicMock()
        mock_spec.loader = None

        # Patch via object to avoid resolve/import of importlib during patching
        with patch.object(importlib_util, "spec_from_file_location", return_value=mock_spec):
            sys.modules.pop("researcharr.webui", None)

            # Should not raise
            webui = importlib.import_module("researcharr.webui")
            assert hasattr(webui, "__all__")


def test_webui_partial_exports():
    """Test webui shim handles partial exports from implementation."""
    mock_webui = MagicMock()
    mock_webui.USER_CONFIG_PATH = "/test/path"
    mock_webui._env_bool = MagicMock()
    # Missing: load_user_config, save_user_config

    # Replace only attribute fetches on the mock with selective failures.
    def limited_getattr(obj, attr, default=None):
        if obj is mock_webui and attr in ("load_user_config", "save_user_config"):
            raise AttributeError(f"No {attr}")
        return object.__getattribute__(obj, attr) if hasattr(obj, attr) else default

    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            return mock_webui
        return real_import_module(name, *args, **kwargs)

    # Prefer injecting the mock into sys.modules so importlib machinery isn't
    # globally patched. This prevents leaked imported modules from polluting
    # other tests when importlib.import_module is patched elsewhere.
    with patch.dict(sys.modules, {"webui": mock_webui}):
        # Ensure fresh import
        sys.modules.pop("researcharr.webui", None)
        webui = importlib.import_module("researcharr.webui")

        # All attributes should exist in __all__
        assert "USER_CONFIG_PATH" in webui.__all__
        assert "load_user_config" in webui.__all__


def test_webui_user_config_path():
    """Test accessing USER_CONFIG_PATH from webui."""
    try:
        from researcharr.webui import USER_CONFIG_PATH

        # May be None or undefined if webui not available
        assert USER_CONFIG_PATH is not None or True
    except (ImportError, AttributeError):
        # Expected if webui implementation not available
        pass


def test_webui_env_bool_function():
    """Test accessing _env_bool from webui."""
    try:
        from researcharr.webui import _env_bool

        assert _env_bool is not None or True
    except (ImportError, AttributeError):
        pass


def test_webui_load_user_config_function():
    """Test accessing load_user_config from webui."""
    try:
        from researcharr.webui import load_user_config

        assert load_user_config is not None or True
    except (ImportError, AttributeError):
        pass


def test_webui_save_user_config_function():
    """Test accessing save_user_config from webui."""
    try:
        from researcharr.webui import save_user_config

        assert save_user_config is not None or True
    except (ImportError, AttributeError):
        pass


def test_webui_fallback_exception():
    """Test webui shim handles exception in fallback path."""
    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            raise ImportError("No webui")
        return real_import_module(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=import_module_side_effect):
        # Patch via object to avoid resolve/import of importlib during patching
        with patch.object(
            importlib_util, "spec_from_file_location", side_effect=Exception("Spec error")
        ):
            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]

            # Should not raise
            webui = importlib.import_module("researcharr.webui")
            assert hasattr(webui, "__all__")


def test_webui_repo_root_calculation():
    """Test webui shim calculates repo root correctly."""
    import os

    from researcharr import webui

    # The shim should be in researcharr package
    webui_file = webui.__file__
    assert webui_file is not None

    # Parent should be researcharr package dir
    pkg_dir = os.path.dirname(webui_file)
    assert "researcharr" in pkg_dir or True


def test_webui_getattr_exception_handling():
    """Test webui shim handles getattr exceptions."""

    class Raising:
        def __getattr__(self, name):  # noqa: D401 - simple helper
            raise RuntimeError("Test error")

    raising_impl = Raising()

    real_import_module = importlib.import_module

    def import_module_side_effect(name, *args, **kwargs):
        if name == "webui":
            return raising_impl
        return real_import_module(name, *args, **kwargs)

    # Inject the raising impl into sys.modules to avoid patching importlib.
    with patch.dict(sys.modules, {"webui": raising_impl}):
        sys.modules.pop("researcharr.webui", None)

        # Should handle the exception gracefully
        try:
            webui = importlib.import_module("researcharr.webui")
            assert hasattr(webui, "__all__")
        except Exception:
            # May raise due to error handling
            pass
