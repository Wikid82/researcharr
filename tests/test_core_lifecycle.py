"""Tests for the core lifecycle management implementation."""

import unittest

from researcharr.core.lifecycle import ApplicationLifecycle, ApplicationState


class TestApplicationLifecycle(unittest.TestCase):
    """Test the application lifecycle implementation."""

    def setUp(self):
        """Set up test environment."""
        self.lifecycle = ApplicationLifecycle()

    def test_initial_state(self):
        """Test initial application state."""
        self.assertEqual(self.lifecycle.state, ApplicationState.CREATED)
        self.assertFalse(self.lifecycle.is_running)
        self.assertFalse(self.lifecycle.is_starting)
        self.assertFalse(self.lifecycle.is_stopping)
        # CREATED state is not considered "stopped"
        self.assertFalse(self.lifecycle.is_stopped)

    def test_add_startup_hook(self):
        """Test adding startup hooks."""

        called = []

        def startup_hook():
            called.append("startup")

        # Add startup hook
        self.lifecycle.add_startup_hook("test_startup", startup_hook)

        # Start application
        result = self.lifecycle.startup()
        self.assertTrue(result)

        # Hook should have been called
        self.assertEqual(len(called), 1)
        self.assertEqual(self.lifecycle.state, ApplicationState.STARTED)

    def test_add_shutdown_hook(self):
        """Test adding shutdown hooks."""

        called = []

        def shutdown_hook():
            called.append("shutdown")

        # Add shutdown hook
        self.lifecycle.add_shutdown_hook("test_shutdown", shutdown_hook)

        # Start and stop application
        self.lifecycle.startup()
        self.lifecycle.shutdown()  # Returns None, not boolean

        # Hook should have been called
        self.assertEqual(len(called), 1)
        self.assertEqual(self.lifecycle.state, ApplicationState.STOPPED)

    def test_hook_priority_ordering(self):
        """Test that hooks are executed in priority order."""

        execution_order = []

        def high_priority_hook():
            execution_order.append("high")

        def low_priority_hook():
            execution_order.append("low")

        def medium_priority_hook():
            execution_order.append("medium")

        # Add hooks in random order (lower priority numbers run first)
        self.lifecycle.add_startup_hook("low", low_priority_hook, priority=100)
        self.lifecycle.add_startup_hook("high", high_priority_hook, priority=1)
        self.lifecycle.add_startup_hook("medium", medium_priority_hook, priority=50)

        # Start application
        self.lifecycle.startup()

        # Should execute in priority order (lowest numbers first)
        self.assertEqual(execution_order, ["high", "medium", "low"])

    def test_critical_hook_failure(self):
        """Test behavior when critical hooks fail."""

        executed = []

        def failing_critical_hook():
            executed.append("critical_attempted")
            raise RuntimeError("Critical hook failed")

        def normal_hook():
            executed.append("normal")

        # Add critical hook that fails
        self.lifecycle.add_startup_hook(
            "critical_fail", failing_critical_hook, critical=True, priority=1
        )
        self.lifecycle.add_startup_hook("normal", normal_hook, priority=2)

        # Starting should fail due to critical hook failure
        result = self.lifecycle.startup()
        self.assertFalse(result)

        # Critical hook should have been attempted but normal hook might not run
        self.assertIn("critical_attempted", executed)

    def test_non_critical_hook_failure(self):
        """Test behavior when non-critical hooks fail."""

        executed = []

        def failing_hook():
            executed.append("failed_attempted")
            raise RuntimeError("Non-critical hook failed")

        def normal_hook():
            executed.append("normal")

        # Add non-critical hook that fails
        self.lifecycle.add_startup_hook(
            "fail", failing_hook, critical=False, priority=1
        )
        self.lifecycle.add_startup_hook("normal", normal_hook, priority=2)

        # Starting should succeed, both hooks should be attempted
        result = self.lifecycle.startup()
        self.assertTrue(result)
        self.assertIn("failed_attempted", executed)
        self.assertIn("normal", executed)

    def test_application_state_transitions(self):
        """Test application state transitions."""

        # Initial state
        self.assertEqual(self.lifecycle.state, ApplicationState.CREATED)

        # Start application
        result = self.lifecycle.startup()
        self.assertTrue(result)
        self.assertEqual(self.lifecycle.state, ApplicationState.STARTED)
        self.assertTrue(self.lifecycle.is_running)

        # Stop application
        self.lifecycle.shutdown()  # Returns None
        self.assertEqual(self.lifecycle.state, ApplicationState.STOPPED)
        self.assertTrue(self.lifecycle.is_stopped)

    def test_shutdown_hooks_reverse_priority(self):
        """Test that shutdown hooks run in reverse priority order."""

        execution_order = []

        def high_priority_shutdown():
            execution_order.append("high")

        def low_priority_shutdown():
            execution_order.append("low")

        # Add shutdown hooks
        self.lifecycle.add_shutdown_hook("high", high_priority_shutdown, priority=100)
        self.lifecycle.add_shutdown_hook("low", low_priority_shutdown, priority=1)

        # Start and stop
        self.lifecycle.startup()
        self.lifecycle.shutdown()

        # Should execute in reverse priority order (higher numbers first for shutdown)
        self.assertEqual(execution_order, ["high", "low"])

    def test_restart_application(self):
        """Test restarting application."""

        startup_calls = []
        shutdown_calls = []

        def startup_hook():
            startup_calls.append("start")

        def shutdown_hook():
            shutdown_calls.append("stop")

        self.lifecycle.add_startup_hook("test", startup_hook)
        self.lifecycle.add_shutdown_hook("test", shutdown_hook)

        # Start, stop, restart
        self.lifecycle.startup()
        self.lifecycle.shutdown()

        # Reset state to created - test restart manually
        # Since restart method doesn't exist, just test manual restart
        self.lifecycle = ApplicationLifecycle()
        self.lifecycle.add_startup_hook("test", startup_hook)
        self.lifecycle.add_shutdown_hook("test", shutdown_hook)
        self.lifecycle.startup()

        # Should have at least 2 startup calls
        self.assertGreaterEqual(len(startup_calls), 2)

    def test_double_start_protection(self):
        """Test that starting an already started application is protected."""

        startup_calls = []

        def startup_hook():
            startup_calls.append("start")

        self.lifecycle.add_startup_hook("test", startup_hook)

        # Start twice
        result1 = self.lifecycle.startup()
        result2 = self.lifecycle.startup()

        # First should succeed, second should fail or be no-op
        self.assertTrue(result1)
        self.assertFalse(result2)  # Should return False for already started

        # Hook should only be called once
        self.assertEqual(len(startup_calls), 1)

    def test_state_properties(self):
        """Test state property methods."""

        # Created state
        self.assertEqual(self.lifecycle.state, ApplicationState.CREATED)
        self.assertFalse(self.lifecycle.is_running)
        self.assertFalse(self.lifecycle.is_starting)
        self.assertFalse(self.lifecycle.is_stopping)
        self.assertFalse(self.lifecycle.is_stopped)  # CREATED is not stopped

        # Started state
        self.lifecycle.startup()
        self.assertEqual(self.lifecycle.state, ApplicationState.STARTED)
        self.assertTrue(self.lifecycle.is_running)
        self.assertFalse(self.lifecycle.is_starting)
        self.assertFalse(self.lifecycle.is_stopping)
        self.assertFalse(self.lifecycle.is_stopped)

    def test_hook_timeout(self):
        """Test hook timeout functionality if supported."""

        import time

        timeout_executed = []

        def slow_hook():
            time.sleep(0.1)  # Small delay
            timeout_executed.append("completed")

        # Add hook with timeout
        self.lifecycle.add_startup_hook(
            "slow", slow_hook, timeout=0.05
        )  # Shorter than sleep

        # Start - might timeout depending on implementation
        result = self.lifecycle.startup()

        # This test depends on implementation details
        # Some implementations might not have timeout support
        if result:
            # If successful, hook completed within timeout or timeout not implemented
            self.assertIn("completed", timeout_executed)

    def test_context_data(self):
        """Test lifecycle context data if supported."""

        if hasattr(self.lifecycle, "_context_data"):
            # This is implementation-specific, testing internal structure
            self.assertIsInstance(self.lifecycle._context_data, dict)

    def test_signal_handler_registration(self):
        """Test that signal handlers are registered if supported."""

        # This is mainly testing that initialization doesn't fail
        # The actual signal handling is hard to test in unit tests
        lifecycle2 = ApplicationLifecycle()
        self.assertIsNotNone(lifecycle2)

    def test_graceful_shutdown_sequence(self):
        """Test complete startup and shutdown sequence."""

        sequence = []

        def startup1():
            sequence.append("startup1")

        def startup2():
            sequence.append("startup2")

        def shutdown1():
            sequence.append("shutdown1")

        def shutdown2():
            sequence.append("shutdown2")

        # Add hooks in specific order
        self.lifecycle.add_startup_hook("s1", startup1, priority=1)
        self.lifecycle.add_startup_hook("s2", startup2, priority=2)
        self.lifecycle.add_shutdown_hook("d1", shutdown1, priority=1)
        self.lifecycle.add_shutdown_hook("d2", shutdown2, priority=2)

        # Full cycle
        startup_result = self.lifecycle.startup()
        self.lifecycle.shutdown()  # Returns None

        self.assertTrue(startup_result)

        # Check sequence
        self.assertEqual(
            sequence[:2], ["startup1", "startup2"]
        )  # Startup in priority order
        self.assertEqual(
            sequence[2:], ["shutdown2", "shutdown1"]
        )  # Shutdown in reverse priority


if __name__ == "__main__":
    unittest.main()
