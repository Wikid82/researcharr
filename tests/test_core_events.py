"""Tests for the core event system implementation."""

import unittest

from researcharr.core.events import Event, EventBus


class TestEventBus(unittest.TestCase):
    """Test the event bus implementation."""

    def setUp(self):
        """Set up test environment."""
        self.event_bus = EventBus()

    def test_subscribe_and_publish(self):
        """Test basic event subscription and publishing."""

        handler_calls = []

        def test_handler(event: Event):
            handler_calls.append(event.data)

        # Subscribe to event
        self.event_bus.subscribe("test.event", test_handler)

        # Publish event using simple method
        self.event_bus.publish_simple("test.event", {"message": "hello"})

        # Handler should have been called
        self.assertEqual(len(handler_calls), 1)
        self.assertEqual(handler_calls[0]["message"], "hello")

    def test_publish_event_object(self):
        """Test publishing Event objects directly."""

        handler_calls = []

        def test_handler(event: Event):
            handler_calls.append(event)

        # Subscribe to event
        self.event_bus.subscribe("test.event", test_handler)

        # Create and publish event object
        event = Event(name="test.event", data={"key": "value"}, source="test")
        self.event_bus.publish(event)

        # Handler should have been called
        self.assertEqual(len(handler_calls), 1)
        received_event = handler_calls[0]
        self.assertEqual(received_event.name, "test.event")
        self.assertEqual(received_event.data["key"], "value")
        self.assertEqual(received_event.source, "test")

    def test_multiple_subscribers(self):
        """Test multiple subscribers to same event."""

        handler1_calls = []
        handler2_calls = []

        def handler1(event: Event):
            handler1_calls.append(event.data)

        def handler2(event: Event):
            handler2_calls.append(event.data)

        # Subscribe multiple handlers
        self.event_bus.subscribe("test.event", handler1)
        self.event_bus.subscribe("test.event", handler2)

        # Publish event
        self.event_bus.publish_simple("test.event", {"count": 1})

        # Both handlers should have been called
        self.assertEqual(len(handler1_calls), 1)
        self.assertEqual(len(handler2_calls), 1)
        self.assertEqual(handler1_calls[0]["count"], 1)
        self.assertEqual(handler2_calls[0]["count"], 1)

    def test_unsubscribe(self):
        """Test unsubscribing from events."""

        handler_calls = []

        def test_handler(event: Event):
            handler_calls.append(event.data)

        # Subscribe and publish
        self.event_bus.subscribe("test.event", test_handler)
        self.event_bus.publish_simple("test.event", {"message": "first"})

        # Unsubscribe
        result = self.event_bus.unsubscribe("test.event", test_handler)
        self.assertTrue(result)  # Should return True when handler found

        self.event_bus.publish_simple("test.event", {"message": "second"})

        # Only first event should have been handled
        self.assertEqual(len(handler_calls), 1)
        self.assertEqual(handler_calls[0]["message"], "first")

    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing non-existent handler."""

        def test_handler(event: Event):
            pass

        # Try to unsubscribe handler that was never subscribed
        result = self.event_bus.unsubscribe("test.event", test_handler)
        self.assertFalse(result)  # Should return False when handler not found

    def test_wildcard_subscription(self):
        """Test wildcard event subscription."""

        handler_calls = []

        def wildcard_handler(event: Event):
            handler_calls.append(event.name)

        # Subscribe to all events
        self.event_bus.subscribe_all(wildcard_handler)

        # Publish multiple events
        self.event_bus.publish_simple("test.event1", {})
        self.event_bus.publish_simple("test.event2", {})
        self.event_bus.publish_simple("other.event", {})

        # Should have received all events
        self.assertEqual(len(handler_calls), 3)
        self.assertIn("test.event1", handler_calls)
        self.assertIn("test.event2", handler_calls)
        self.assertIn("other.event", handler_calls)

    def test_unsubscribe_wildcard(self):
        """Test unsubscribing from wildcard events."""

        handler_calls = []

        def wildcard_handler(event: Event):
            handler_calls.append(event.name)

        # Subscribe and publish
        self.event_bus.subscribe_all(wildcard_handler)
        self.event_bus.publish_simple("test.event", {})

        # Unsubscribe from all
        result = self.event_bus.unsubscribe_all(wildcard_handler)
        self.assertTrue(result)

        self.event_bus.publish_simple("test.event2", {})

        # Only first event should have been handled
        self.assertEqual(len(handler_calls), 1)
        self.assertEqual(handler_calls[0], "test.event")

    def test_error_handling_in_handlers(self):
        """Test error handling when event handlers fail."""

        successful_calls = []

        def failing_handler(event: Event):
            raise ValueError("Handler failed")

        def successful_handler(event: Event):
            successful_calls.append(event.data)

        # Subscribe both handlers
        self.event_bus.subscribe("test.event", failing_handler)
        self.event_bus.subscribe("test.event", successful_handler)

        # Publish event - should not raise exception even if one handler fails
        self.event_bus.publish_simple("test.event", {"test": "data"})

        # Successful handler should still have been called
        self.assertEqual(len(successful_calls), 1)

    def test_no_subscribers(self):
        """Test publishing to event with no subscribers."""

        # Should not raise exception
        self.event_bus.publish_simple("nonexistent.event", {"data": "test"})

    def test_event_history(self):
        """Test event history functionality."""

        # Publish some events
        self.event_bus.publish_simple("event1", {"data": 1})
        self.event_bus.publish_simple("event2", {"data": 2})
        self.event_bus.publish_simple("event1", {"data": 3})

        # Get all history
        history = self.event_bus.get_event_history()
        self.assertEqual(len(history), 3)

        # Get filtered history
        event1_history = self.event_bus.get_event_history("event1")
        self.assertEqual(len(event1_history), 2)
        self.assertEqual(event1_history[0].data["data"], 1)
        self.assertEqual(event1_history[1].data["data"], 3)

        # Get limited history
        limited_history = self.event_bus.get_event_history(limit=2)
        self.assertEqual(len(limited_history), 2)

    def test_clear_history(self):
        """Test clearing event history."""

        # Publish event
        self.event_bus.publish_simple("test.event", {"data": "test"})

        # Check history exists
        history = self.event_bus.get_event_history()
        self.assertGreater(len(history), 0)

        # Clear history
        self.event_bus.clear_history()

        # Check history is cleared
        history = self.event_bus.get_event_history()
        self.assertEqual(len(history), 0)

    def test_subscriber_count(self):
        """Test getting subscriber count."""

        def handler1(event: Event):
            pass

        def handler2(event: Event):
            pass

        # Check initial count
        self.assertEqual(self.event_bus.get_subscriber_count("test.event"), 0)
        self.assertEqual(self.event_bus.get_subscriber_count(), 0)

        # Subscribe handlers
        self.event_bus.subscribe("test.event", handler1)
        self.event_bus.subscribe("test.event", handler2)
        self.event_bus.subscribe("other.event", handler1)
        self.event_bus.subscribe_all(handler1)

        # Check counts
        self.assertEqual(self.event_bus.get_subscriber_count("test.event"), 2)
        self.assertEqual(self.event_bus.get_subscriber_count("other.event"), 1)
        self.assertEqual(
            self.event_bus.get_subscriber_count(), 4
        )  # 3 specific + 1 wildcard

    def test_list_events(self):
        """Test listing events with subscribers."""

        def handler(event: Event):
            pass

        # Initially no events
        events = self.event_bus.list_events()
        self.assertEqual(len(events), 0)

        # Subscribe to events
        self.event_bus.subscribe("event1", handler)
        self.event_bus.subscribe("event2", handler)

        # Check event list
        events = self.event_bus.list_events()
        self.assertEqual(len(events), 2)
        self.assertIn("event1", events)
        self.assertIn("event2", events)


if __name__ == "__main__":
    unittest.main()
