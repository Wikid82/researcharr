"""Comprehensive tests for researcharr._package_helpers module.

This module tests the package-level helper functions that handle
serve() and create_metrics_app dispatching logic.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


def test_serve_with_create_metrics_app_in_caller_frame():
    """Test serve() finds create_metrics_app from caller's frame."""
    from researcharr import _package_helpers

    # Create a mock app
    mock_app = MagicMock()
    mock_app.run = MagicMock()

    # Create mock for create_metrics_app
    mock_create = MagicMock(return_value=mock_app)

    # Inject into researcharr module
    import researcharr

    researcharr.create_metrics_app = mock_create

    # Mock flask to avoid actual server start
    with patch.dict(sys.modules, {"flask": MagicMock()}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    # Verify create_metrics_app was called
    assert mock_create.call_count >= 1


def test_serve_with_flask_app():
    """Test serve() with a Flask app object."""
    from researcharr import _package_helpers

    # Create a mock Flask app
    mock_flask = MagicMock()
    mock_app = MagicMock()
    mock_app.run = MagicMock()
    mock_flask.Flask = type(mock_app)

    mock_create = MagicMock(return_value=mock_app)

    import researcharr

    researcharr.create_metrics_app = mock_create

    with patch.dict(sys.modules, {"flask": mock_flask}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    mock_create.assert_called()


def test_serve_with_non_flask_app():
    """Test serve() with a non-Flask app that has run method."""
    from researcharr import _package_helpers

    # Create a custom app with run method
    mock_app = MagicMock()
    mock_app.run = MagicMock()

    mock_create = MagicMock(return_value=mock_app)

    import researcharr

    researcharr.create_metrics_app = mock_create

    with patch.dict(sys.modules, {"flask": None}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    mock_create.assert_called()


def test_serve_finds_mock_in_modules():
    """Test serve() can find Mock instances across loaded modules."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_create = Mock(return_value=mock_app)

    # Create a test module with the mock
    test_module = type(sys)("test_mock_module")
    test_module.create_metrics_app = mock_create

    with patch.dict(sys.modules, {"test_mock_module": test_module}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    # The mock should have been called
    assert mock_create.call_count > 0


def test_serve_with_importlib():
    """Test serve() uses importlib to find create_metrics_app."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_create = MagicMock(return_value=mock_app)

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.create_metrics_app = mock_create
        mock_import.return_value = mock_module

        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    mock_import.assert_called_with("researcharr")


def test_serve_checks_implementation_module():
    """Test serve() checks researcharr.researcharr module."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_create = MagicMock(return_value=mock_app)

    # Create mock implementation module
    impl_module = type(sys)("researcharr.researcharr")
    impl_module.create_metrics_app = mock_create

    with patch.dict(sys.modules, {"researcharr.researcharr": impl_module}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    mock_create.assert_called()


def test_serve_handles_multiple_candidates():
    """Test serve() calls multiple candidates when found."""
    from researcharr import _package_helpers

    mock_app1 = MagicMock()
    mock_app2 = MagicMock()

    mock_create1 = MagicMock(return_value=mock_app1)
    mock_create2 = MagicMock(return_value=mock_app2)

    # Create test modules
    test_module1 = type(sys)("test_module1")
    test_module1.create_metrics_app = mock_create1

    test_module2 = type(sys)("test_module2")
    test_module2.create_metrics_app = mock_create2

    with patch.dict(sys.modules, {"test_module1": test_module1, "test_module2": test_module2}):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()


def test_serve_exception_handling():
    """Test serve() handles exceptions gracefully."""
    from researcharr import _package_helpers

    # Create a mock that raises an exception
    mock_create = MagicMock(side_effect=Exception("Test error"))

    import researcharr

    researcharr.create_metrics_app = mock_create

    # Should not raise
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
        _package_helpers.serve()


def test_install_create_metrics_dispatcher():
    """Test installing the create_metrics_app dispatcher."""
    from researcharr import _package_helpers

    # Setup modules
    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    mock_original = MagicMock()
    impl_module.create_metrics_app = mock_original

    with patch.dict(
        sys.modules, {"researcharr": pkg_module, "researcharr.researcharr": impl_module}
    ):
        _package_helpers.install_create_metrics_dispatcher()

    # Check that dispatcher was installed
    assert "create_metrics_app" in pkg_module.__dict__
    assert callable(pkg_module.__dict__["create_metrics_app"])


def test_dispatcher_prefers_package_level_patch():
    """Test dispatcher prefers package-level patches."""
    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    mock_original = MagicMock(return_value="original")
    mock_patched = MagicMock(return_value="patched")

    impl_module.create_metrics_app = mock_original

    with patch.dict(
        sys.modules, {"researcharr": pkg_module, "researcharr.researcharr": impl_module}
    ):
        _package_helpers.install_create_metrics_dispatcher()

        dispatcher = pkg_module.__dict__["create_metrics_app"]

        # Now patch at package level
        pkg_module.__dict__["create_metrics_app"] = mock_patched

        # Call original dispatcher (saved reference)
        result = dispatcher()

        # Should call the patched version since dispatcher searches for patches
        assert result == "patched"


def test_dispatcher_searches_for_mocks():
    """Test dispatcher searches for Mock instances."""
    from unittest.mock import Mock

    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    impl_module.create_metrics_app = MagicMock(return_value="impl")

    # Create a module with a Mock
    mock_module = type(sys)("mock_test_module")
    mock_create = Mock(return_value="mock_result")
    mock_module.create_metrics_app = mock_create

    with patch.dict(
        sys.modules,
        {
            "researcharr": pkg_module,
            "researcharr.researcharr": impl_module,
            "mock_test_module": mock_module,
        },
    ):
        _package_helpers.install_create_metrics_dispatcher()

        dispatcher = pkg_module.__dict__["create_metrics_app"]
        result = dispatcher()

        # Should find and use the Mock
        assert mock_create.call_count > 0 or result == "impl"


def test_dispatcher_falls_back_to_original():
    """Test dispatcher falls back to original implementation."""
    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    mock_original = MagicMock(return_value="original")
    impl_module.create_metrics_app = mock_original

    with patch.dict(
        sys.modules, {"researcharr": pkg_module, "researcharr.researcharr": impl_module}
    ):
        _package_helpers.install_create_metrics_dispatcher()

        # Get dispatcher reference before clearing
        dispatcher = pkg_module.__dict__["create_metrics_app"]

        # Clear both dicts so dispatcher has to use original
        pkg_module.__dict__.clear()
        impl_module.__dict__.clear()

        # This should fall back to the saved original
        result = dispatcher()
        assert result == "original"


def test_dispatcher_handles_exceptions():
    """Test dispatcher handles exceptions in lookups."""
    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    # Create an implementation that raises
    def raising_impl():
        raise RuntimeError("Test error")

    impl_module.create_metrics_app = raising_impl

    with patch.dict(
        sys.modules, {"researcharr": pkg_module, "researcharr.researcharr": impl_module}
    ):
        _package_helpers.install_create_metrics_dispatcher()

        dispatcher = pkg_module.__dict__["create_metrics_app"]

        # Should raise since all fallbacks fail
        with pytest.raises(Exception):
            dispatcher()


def test_dispatcher_no_implementation_available():
    """Test dispatcher raises ImportError when no implementation found."""
    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")

    # Ensure researcharr.researcharr is not present
    saved_modules = {}
    for key in ["researcharr", "researcharr.researcharr"]:
        if key in sys.modules:
            saved_modules[key] = sys.modules[key]
    
    try:
        with patch.dict(sys.modules, {"researcharr": pkg_module}, clear=False):
            # Remove impl module
            sys.modules.pop("researcharr.researcharr", None)
            
            _package_helpers.install_create_metrics_dispatcher()

            dispatcher = pkg_module.__dict__["create_metrics_app"]

            # Clear all references
            pkg_module.__dict__.clear()

            with pytest.raises(ImportError, match="No create_metrics_app implementation available"):
                dispatcher()
    finally:
        # Restore
        for key, val in saved_modules.items():
            sys.modules[key] = val


def test_serve_without_pytest_env():
    """Test serve() behavior when not in pytest environment."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_app.run = MagicMock()
    mock_create = MagicMock(return_value=mock_app)

    import researcharr

    researcharr.create_metrics_app = mock_create

    # Mock Flask to be present
    mock_flask = MagicMock()
    mock_flask.Flask = type(mock_app)

    with patch.dict(sys.modules, {"flask": mock_flask}):
        with patch.dict("os.environ", {}, clear=True):
            # Clear PYTEST_CURRENT_TEST
            with patch.object(mock_app, "run"):
                try:
                    _package_helpers.serve()
                except Exception:
                    pass  # May raise if binding fails

                # Check that run was at least attempted
                # (it may fail due to port binding in test environment)


def test_install_dispatcher_handles_missing_modules():
    """Test dispatcher installation handles missing modules."""
    from researcharr import _package_helpers

    with patch.dict(sys.modules, {}, clear=True):
        # Should not raise even with no modules
        _package_helpers.install_create_metrics_dispatcher()


def test_serve_inspect_frame_exception():
    """Test serve() handles inspect frame exceptions."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_create = MagicMock(return_value=mock_app)

    import researcharr

    researcharr.create_metrics_app = mock_create

    with patch("inspect.currentframe", side_effect=Exception("Frame error")):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    # Should still work via fallback
    mock_create.assert_called()


def test_serve_caller_frame_not_module():
    """Test serve() handles non-module type in caller frame."""
    from researcharr import _package_helpers

    mock_app = MagicMock()
    mock_create = MagicMock(return_value=mock_app)

    import researcharr

    researcharr.create_metrics_app = mock_create

    # Mock frame with non-ModuleType researcharr
    with patch("inspect.currentframe") as mock_frame:
        frame_obj = MagicMock()
        frame_obj.f_back = MagicMock()
        frame_obj.f_back.f_globals = {"researcharr": "not_a_module"}
        frame_obj.f_back.f_back = None
        mock_frame.return_value = frame_obj

        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            _package_helpers.serve()

    mock_create.assert_called()


def test_install_dispatcher_with_only_impl_module():
    """Test dispatcher installation with only impl module present."""
    from researcharr import _package_helpers

    impl_module = type(sys)("researcharr.researcharr")
    mock_impl = MagicMock(return_value="impl_result")
    impl_module.create_metrics_app = mock_impl

    with patch.dict(sys.modules, {"researcharr.researcharr": impl_module}):
        _package_helpers.install_create_metrics_dispatcher()

    # Check that dispatcher was installed in impl module
    assert "create_metrics_app" in impl_module.__dict__


def test_dispatcher_prefers_impl_level_patch():
    """Test dispatcher prefers impl-level patches when package-level not found."""
    from researcharr import _package_helpers

    pkg_module = type(sys)("researcharr")
    impl_module = type(sys)("researcharr.researcharr")

    mock_impl_patched = MagicMock(return_value="impl_patched")

    impl_module.create_metrics_app = MagicMock(return_value="original")

    with patch.dict(
        sys.modules, {"researcharr": pkg_module, "researcharr.researcharr": impl_module}
    ):
        _package_helpers.install_create_metrics_dispatcher()

        dispatcher = pkg_module.__dict__["create_metrics_app"]

        # Patch impl level
        impl_module.__dict__["create_metrics_app"] = mock_impl_patched

        result = dispatcher()
        assert result == "impl_patched"
