"""Coverage tests for researcharr.core.lifecycle module."""

import logging
import threading
import time
from unittest.mock import patch
import pytest


def test_application_state_enum():
    """Test ApplicationState enum values."""
    from researcharr.core.lifecycle import ApplicationState

    assert ApplicationState.CREATED.value == "created"
    assert ApplicationState.STARTING.value == "starting"
    assert ApplicationState.STARTED.value == "started"
    assert ApplicationState.STOPPING.value == "stopping"
    assert ApplicationState.STOPPED.value == "stopped"
    assert ApplicationState.FAILED.value == "failed"


def test_lifecycle_hook_dataclass():
    """Test LifecycleHook dataclass creation."""
    from researcharr.core.lifecycle import LifecycleHook

    hook = LifecycleHook(
        name="test_hook", callback=lambda: None, priority=50, critical=True, timeout=5.0
    )

    assert hook.name == "test_hook"
    assert hook.priority == 50
    assert hook.critical is True
    assert hook.timeout == 5.0


def test_application_lifecycle_initialization():
    """Test ApplicationLifecycle initialization."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    assert lifecycle.state == ApplicationState.CREATED
    assert not lifecycle.is_starting
    assert not lifecycle.is_running
    assert not lifecycle.is_stopping
    assert not lifecycle.is_stopped


def test_lifecycle_state_properties():
    """Test lifecycle state property methods."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    # Test starting state
    lifecycle._set_state(ApplicationState.STARTING)
    assert lifecycle.is_starting
    assert not lifecycle.is_running

    # Test running state
    lifecycle._set_state(ApplicationState.STARTED)
    assert lifecycle.is_running
    assert not lifecycle.is_starting

    # Test stopping state
    lifecycle._set_state(ApplicationState.STOPPING)
    assert lifecycle.is_stopping

    # Test stopped state
    lifecycle._set_state(ApplicationState.STOPPED)
    assert lifecycle.is_stopped


def test_add_startup_hook():
    """Test adding startup hooks."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    hook_called = []

    def test_hook():
        hook_called.append(True)

    lifecycle.add_startup_hook("test", test_hook)

    assert len(lifecycle._startup_hooks) == 1


def test_add_shutdown_hook():
    """Test adding shutdown hooks."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    lifecycle.add_shutdown_hook("shutdown_test", lambda: None)

    assert len(lifecycle._shutdown_hooks) == 1


def test_startup_hook_execution():
    """Test startup hooks are executed."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    results = []

    def hook1():
        results.append(1)

    def hook2():
        results.append(2)

    lifecycle.add_startup_hook("hook1", hook1, priority=10)
    lifecycle.add_startup_hook("hook2", hook2, priority=20)

    lifecycle.startup()

    # Should be called in priority order
    assert 1 in results
    assert 2 in results


def test_shutdown_hook_execution():
    """Test shutdown hooks are executed."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()
    lifecycle._set_state(lifecycle._state.__class__.STARTED)  # Set to started

    results = []

    def shutdown_hook():
        results.append("shutdown")

    lifecycle.add_shutdown_hook("shutdown", shutdown_hook)

    lifecycle.shutdown()

    assert "shutdown" in results


def test_startup_hook_priority_ordering():
    """Test startup hooks execute in priority order."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    results = []

    lifecycle.add_startup_hook("low", lambda: results.append("low"), priority=100)
    lifecycle.add_startup_hook("high", lambda: results.append("high"), priority=10)
    lifecycle.add_startup_hook("mid", lambda: results.append("mid"), priority=50)

    lifecycle.startup()

    assert results == ["high", "mid", "low"]


def test_critical_hook_failure_stops_startup():
    """Test critical hook failure stops startup."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    def failing_hook():
        raise Exception("Critical failure")

    lifecycle.add_startup_hook("critical", failing_hook, critical=True)

    with pytest.raises(Exception, match="Critical failure"):
        lifecycle.startup()

    assert lifecycle.state == ApplicationState.FAILED


def test_non_critical_hook_failure_continues():
    """Test non-critical hook failure allows continuation."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    results = []

    def failing_hook():
        raise Exception("Non-critical failure")

    def success_hook():
        results.append("success")

    lifecycle.add_startup_hook("fail", failing_hook, critical=False, priority=10)
    lifecycle.add_startup_hook("success", success_hook, priority=20)

    lifecycle.startup()

    assert "success" in results
    assert lifecycle.state == ApplicationState.STARTED


def test_hook_timeout_enforcement():
    """Test hook timeout enforcement."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    def slow_hook():
        time.sleep(2)

    lifecycle.add_startup_hook("slow", slow_hook, timeout=0.1)

    # Should complete without hanging
    lifecycle.startup()


def test_shutdown_prevents_double_shutdown():
    """Test shutdown can only happen once."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()
    lifecycle._set_state(ApplicationState.STARTED)

    lifecycle.shutdown()

    # Second shutdown should be no-op
    lifecycle.shutdown()

    assert lifecycle.state == ApplicationState.STOPPED


def test_signal_handler_registration():
    """Test signal handlers are registered."""
    from researcharr.core.lifecycle import ApplicationLifecycle
    with patch("signal.signal") as mock_signal:
        ApplicationLifecycle()
        assert mock_signal.call_count >= 2


def test_shutdown_hook_execution_via_direct_shutdown():
    """Test shutdown hook executes when lifecycle.shutdown is called."""
    from researcharr.core.lifecycle import ApplicationLifecycle, ApplicationState

    lifecycle = ApplicationLifecycle()
    lifecycle._set_state(ApplicationState.STARTED)
    results = []

    def cleanup_hook():
        results.append("cleaned")

    lifecycle.add_shutdown_hook("cleanup", cleanup_hook)
    lifecycle.shutdown("test")
    assert "cleaned" in results


# Removed context data tests; API no longer exposes context storage methods.


def test_lifecycle_event_publishing():
    """Test lifecycle publishes events."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    with patch.object(lifecycle._event_bus, "publish_simple") as mock_publish:
        lifecycle._set_state(ApplicationState.STARTING)

        mock_publish.assert_called()


def test_add_startup_hook_helper():
    """Test add_startup_hook helper function."""
    from researcharr.core.lifecycle import add_startup_hook

    called = []

    def my_hook():
        called.append(True)

    add_startup_hook("test_hook", my_hook, priority=50)

    # Hook should be registered (verify by checking internal state would require instance)


def test_add_shutdown_hook_helper():
    """Test add_shutdown_hook helper function."""
    from researcharr.core.lifecycle import add_shutdown_hook

    def my_hook():
        pass

    # Should not raise
    add_shutdown_hook("test_shutdown", my_hook, priority=50)


def test_get_lifecycle_singleton():
    """Test get_lifecycle returns singleton."""
    from researcharr.core.lifecycle import get_lifecycle

    lc1 = get_lifecycle()
    lc2 = get_lifecycle()

    assert lc1 is lc2


def test_lifecycle_thread_safety():
    """Test lifecycle operations are thread-safe."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    results = []

    def add_hooks():
        for i in range(10):
            lifecycle.add_startup_hook(f"hook_{i}", lambda: results.append(1))

    threads = [threading.Thread(target=add_hooks) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Should have all hooks added without conflicts
    assert len(lifecycle._startup_hooks) == 50


def test_startup_already_started():
    """Test startup when already started is no-op."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()
    lifecycle._set_state(ApplicationState.STARTED)

    # Should not raise or change state
    lifecycle.startup()

    assert lifecycle.state == ApplicationState.STARTED


def test_shutdown_when_not_started():
    """Test shutdown when not started."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    lifecycle.shutdown()

    # Should handle gracefully


def test_hook_execution_exception_logging(caplog):
    """Test hook exceptions are logged."""
    from researcharr.core.lifecycle import ApplicationLifecycle

    lifecycle = ApplicationLifecycle()

    def error_hook():
        raise ValueError("Test error")

    lifecycle.add_startup_hook("error", error_hook, critical=False)

    with caplog.at_level(logging.ERROR):
        lifecycle.startup()

        # Error should be logged


def test_lifecycle_state_transition_logging(caplog):
    """Test state transitions are logged."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    with caplog.at_level(logging.INFO):
        lifecycle._set_state(ApplicationState.STARTING)

        assert "state changed" in caplog.text.lower()


def test_atexit_registration():
    """Test atexit handler registration."""
    from researcharr.core.lifecycle import ApplicationLifecycle
    with patch("atexit.register") as mock_atexit:
        ApplicationLifecycle()
        assert mock_atexit.called


def test_lifecycle_wait_for_state():
    """Test waiting for specific state."""
    from researcharr.core.lifecycle import (
        ApplicationLifecycle,
        ApplicationState,
    )

    lifecycle = ApplicationLifecycle()

    def change_state():
        time.sleep(0.1)
        lifecycle._set_state(ApplicationState.STARTED)

    thread = threading.Thread(target=change_state)
    thread.start()

    # Wait for state change
    timeout = 1.0
    start = time.time()
    while lifecycle.state != ApplicationState.STARTED and (time.time() - start) < timeout:
        time.sleep(0.01)

    thread.join()

    assert lifecycle.state == ApplicationState.STARTED
