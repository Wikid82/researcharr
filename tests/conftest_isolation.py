"""
Autouse fixtures for test isolation and state cleanup.

These fixtures run automatically for every test to ensure proper isolation:
- Reset logging configuration
- Clean up Prometheus collectors
- Reset module state (factory, researcharr)
- Clear import caches

This helps prevent flaky tests caused by global state pollution.
"""

import logging
import sys
from collections.abc import Generator

import pytest

# Try to import Prometheus client, but don't fail if it's not available
try:
    from prometheus_client import REGISTRY

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False


@pytest.fixture(autouse=True, scope="function")
def isolate_logging() -> Generator[None]:
    """
    Reset logging configuration between tests.

    Saves the current logging state before the test runs and restores it
    afterwards. This prevents tests from interfering with each other's
    logging configuration.
    """
    # Save original state
    original_level = logging.root.level
    original_handlers = logging.root.handlers[:]
    original_filters = logging.root.filters[:]

    yield

    # Restore original state
    logging.root.setLevel(original_level)

    # Remove all handlers that were added during the test
    for handler in logging.root.handlers[:]:
        if handler not in original_handlers:
            try:
                handler.close()
            except Exception:
                pass
            logging.root.removeHandler(handler)

    # Restore original handlers if they were removed
    for handler in original_handlers:
        if handler not in logging.root.handlers:
            logging.root.addHandler(handler)

    # Restore original filters
    logging.root.filters = original_filters[:]


@pytest.fixture(autouse=True, scope="function")
def isolate_prometheus() -> Generator[None]:
    """
    Clean up Prometheus collectors between tests.

    Records which collectors exist before the test and removes any new
    collectors added during the test. This prevents metric conflicts between
    tests.
    """
    if not HAS_PROMETHEUS:
        yield
        return

    # Get list of collectors before test
    before = set(REGISTRY._collector_to_names.keys())

    yield

    # Remove collectors added during test
    after = set(REGISTRY._collector_to_names.keys())
    for collector in after - before:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            # Ignore errors during cleanup - collector might have been
            # unregistered already
            pass


@pytest.fixture(autouse=True, scope="function")
def isolate_factory_state() -> Generator[None]:
    """
    Reset factory module state between tests.

    Cleans up module-level attributes that might be set during tests to
    prevent state leakage. This is particularly important for factory tests
    that check for specific attributes.
    
    Also resets the _RuntimeConfig singleton that is used by tests to patch
    runtime behavior.
    """
    # Modules that might have state set during tests
    factory_modules = [
        "researcharr.factory",
        "factory",
        "researcharr.researcharr",
        "researcharr",
    ]

    # Attributes that should be cleaned up after tests
    transient_attrs = [
        "_running_in_image",
        "_upgrade_available",
        "_api_generated",
        "_app_created",
        "_metrics_app",
    ]

    yield

    # Clean up transient attributes from all factory-related modules
    for mod_name in factory_modules:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            for attr in transient_attrs:
                if hasattr(mod, attr):
                    try:
                        delattr(mod, attr)
                    except (AttributeError, TypeError):
                        # Some attributes might be read-only or not deletable
                        pass
    
    # Reset _RuntimeConfig singleton state
    # This is critical for tests that patch _RuntimeConfig behavior
    for mod_name in factory_modules:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "_RuntimeConfig"):
                # Reset the class-level override attributes
                mod._RuntimeConfig._running_in_image_override = None
                mod._RuntimeConfig._webui_override = None


@pytest.fixture(autouse=True, scope="function")
def isolate_environment() -> Generator[None]:
    """
    Save and restore environment variables between tests.

    Some tests modify environment variables. This fixture ensures those
    changes don't affect other tests.
    """
    import os

    # Save current environment
    original_env = os.environ.copy()

    yield

    # Restore environment
    # Remove any keys that were added
    for key in list(os.environ.keys()):
        if key not in original_env:
            del os.environ[key]

    # Restore original values
    for key, value in original_env.items():
        os.environ[key] = value


# Note: We don't use autouse for module-level isolation because it would
# slow down tests significantly. Instead, specific tests that need fresh
# module imports should use pytest's monkeypatch or importlib.reload()
# explicitly.
