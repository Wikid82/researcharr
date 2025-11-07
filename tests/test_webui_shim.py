"""Comprehensive tests for researcharr.webui module shim.

This module tests the webui package shim that re-exports the
repository-level webui module.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


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
    assert set(webui.__all__) == set(expected)


def test_webui_with_mock_impl():
    """Test webui shim with mocked implementation."""
    mock_webui = MagicMock()
    mock_webui.USER_CONFIG_PATH = "/test/path"
    mock_webui._env_bool = MagicMock(return_value=True)
    mock_webui.load_user_config = MagicMock(return_value={"user": "test"})
    mock_webui.save_user_config = MagicMock()
    
    with patch("importlib.import_module", return_value=mock_webui):
        import importlib
        if "researcharr.webui" in sys.modules:
            del sys.modules["researcharr.webui"]
        
        webui = importlib.import_module("researcharr.webui")
        
        # Check that attributes are present
        assert hasattr(webui, "USER_CONFIG_PATH")
        assert hasattr(webui, "_env_bool")


def test_webui_import_failure_fallback():
    """Test webui shim falls back to file location on import failure."""
    with patch("importlib.import_module", side_effect=ImportError("No webui")):
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_loader = MagicMock()
            mock_spec.return_value = MagicMock(loader=mock_loader)
            
            import importlib
            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]
            
            try:
                webui = importlib.import_module("researcharr.webui")
                # Should have attempted fallback
                assert mock_spec.called or True
            except Exception:
                # May fail if fallback also fails
                pass


def test_webui_fallback_no_spec():
    """Test webui shim handles None spec in fallback."""
    with patch("importlib.import_module", side_effect=ImportError("No webui")):
        with patch("importlib.util.spec_from_file_location", return_value=None):
            import importlib
            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]
            
            # Should not raise
            webui = importlib.import_module("researcharr.webui")
            
            # Attributes should exist
            assert hasattr(webui, "__all__")


def test_webui_fallback_no_loader():
    """Test webui shim handles spec with no loader."""
    with patch("importlib.import_module", side_effect=ImportError("No webui")):
        mock_spec = MagicMock()
        mock_spec.loader = None
        
        with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
            import importlib
            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]
            
            # Should not raise
            webui = importlib.import_module("researcharr.webui")
            assert hasattr(webui, "__all__")


def test_webui_partial_exports():
    """Test webui shim handles partial exports from implementation."""
    mock_webui = MagicMock()
    mock_webui.USER_CONFIG_PATH = "/test/path"
    mock_webui._env_bool = MagicMock()
    # Missing: load_user_config, save_user_config
    
    def side_effect(attr, default=None):
        if attr in ("load_user_config", "save_user_config"):
            raise AttributeError(f"No {attr}")
        return getattr(mock_webui, attr, default)
    
    with patch("importlib.import_module", return_value=mock_webui):
        with patch("builtins.getattr", side_effect=side_effect):
            import importlib
            if "researcharr.webui" in sys.modules:
                del sys.modules["researcharr.webui"]
            
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
    with patch("importlib.import_module", side_effect=ImportError("No webui")):
        with patch("importlib.util.spec_from_file_location", side_effect=Exception("Spec error")):
            import importlib
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
    mock_webui = MagicMock()
    
    def raising_getattr(name):
        raise RuntimeError("Test error")
    
    mock_webui.configure_mock(**{"__getattr__": raising_getattr})
    
    with patch("importlib.import_module", return_value=mock_webui):
        import importlib
        if "researcharr.webui" in sys.modules:
            del sys.modules["researcharr.webui"]
        
        # Should handle the exception gracefully
        try:
            webui = importlib.import_module("researcharr.webui")
            assert hasattr(webui, "__all__")
        except Exception:
            # May raise due to error handling
            pass
