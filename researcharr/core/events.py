"""Event Bus for Application-wide Messaging.

Provides a publish-subscribe event system for loose coupling between
application components.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event class."""

    name: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str | None = None

    def __post_init__(self):
        """Ensure timestamp is set."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class EventBus:
    """Thread-safe event bus for publish-subscribe messaging."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._wildcard_subscribers: list[Callable[[Event], None]] = []
        self._lock = threading.RLock()
        self._event_history: list[Event] = []
        self._max_history = 1000

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events with a specific name."""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(handler)
            LOGGER.debug("Subscribed to event: %s", event_name)

    def subscribe_all(self, handler: Callable[[Event], None]) -> None:
        """Subscribe to all events (wildcard subscriber)."""
        with self._lock:
            self._wildcard_subscribers.append(handler)
            LOGGER.debug("Added wildcard event subscriber")

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> bool:
        """Unsubscribe from events. Returns True if handler was found and removed."""
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(handler)
                    LOGGER.debug("Unsubscribed from event: %s", event_name)
                    return True
                except ValueError:
                    pass
            return False

    def unsubscribe_all(self, handler: Callable[[Event], None]) -> bool:
        """Unsubscribe from all events.

        Returns True if handler was found and removed.
        """
        with self._lock:
            try:
                self._wildcard_subscribers.remove(handler)
                LOGGER.debug("Removed wildcard event subscriber")
                return True
            except ValueError:
                return False

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        with self._lock:
            # Store in history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # Notify specific subscribers
            handlers = self._subscribers.get(event.name, []).copy()

            # Notify wildcard subscribers
            handlers.extend(self._wildcard_subscribers.copy())

        # Call handlers outside of lock to avoid deadlocks
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                LOGGER.exception("Error in event handler for event: %s", event.name)

    def publish_simple(self, event_name: str, data: Any = None, source: str | None = None) -> None:
        """Convenience method to publish a simple event."""
        event = Event(name=event_name, data=data, source=source)
        self.publish(event)

    def get_event_history(self, event_name: str | None = None, limit: int = 100) -> list[Event]:
        """Get recent event history, optionally filtered by event name."""
        with self._lock:
            events = self._event_history.copy()

        if event_name:
            events = [e for e in events if e.name == event_name]

        return events[-limit:] if limit > 0 else events

    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._event_history.clear()
            LOGGER.debug("Cleared event history")

    def get_subscriber_count(self, event_name: str | None = None) -> int:
        """Get number of subscribers for an event, or total if event_name is None."""
        with self._lock:
            if event_name:
                return len(self._subscribers.get(event_name, []))
            else:
                total = sum(len(handlers) for handlers in self._subscribers.values())
                total += len(self._wildcard_subscribers)
                return total

    def list_events(self) -> list[str]:
        """List all event names that have subscribers."""
        with self._lock:
            return list(self._subscribers.keys())


# Global event bus instance
_event_bus: EventBus | None = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (mainly for testing)."""
    global _event_bus
    with _event_bus_lock:
        _event_bus = None


# Convenience functions for common operations
def subscribe(event_name: str, handler: Callable[[Event], None]) -> None:
    """Subscribe to events in the global event bus."""
    get_event_bus().subscribe(event_name, handler)


def subscribe_all(handler: Callable[[Event], None]) -> None:
    """Subscribe to all events in the global event bus."""
    get_event_bus().subscribe_all(handler)


def publish(event: Event) -> None:
    """Publish an event to the global event bus."""
    get_event_bus().publish(event)


def publish_simple(event_name: str, data: Any = None, source: str | None = None) -> None:
    """Publish a simple event to the global event bus."""
    get_event_bus().publish_simple(event_name, data, source)


# Common event names used throughout the application
class Events:
    """Common event name constants."""

    # Application lifecycle
    APP_STARTING = "app.starting"
    APP_STARTED = "app.started"
    APP_STOPPING = "app.stopping"
    APP_STOPPED = "app.stopped"

    # Configuration
    CONFIG_LOADED = "config.loaded"
    CONFIG_CHANGED = "config.changed"
    CONFIG_SAVED = "config.saved"

    # Media processing
    MEDIA_DISCOVERED = "media.discovered"
    MEDIA_PROCESSING_STARTED = "media.processing.started"
    MEDIA_PROCESSING_COMPLETED = "media.processing.completed"
    MEDIA_PROCESSING_FAILED = "media.processing.failed"

    # Jobs and tasks
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"

    # Health and monitoring
    HEALTH_CHECK = "health.check"
    METRIC_RECORDED = "metric.recorded"
    ERROR_OCCURRED = "error.occurred"

    # Plugin system
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_ERROR = "plugin.error"

    # Backup and recovery
    BACKUP_CREATED = "backup.created"
    BACKUP_FAILED = "backup.failed"
    BACKUP_RESTORED = "backup.restored"
    BACKUP_RESTORE_FAILED = "backup.restore_failed"
    BACKUP_PRUNED = "backup.pruned"
    BACKUP_STALE = "backup.stale"
    BACKUP_VALIDATION_FAILED = "backup.validation_failed"
    PRE_RESTORE_SNAPSHOT_CREATED = "backup.pre_restore_snapshot_created"
    RESTORE_ROLLBACK_EXECUTED = "backup.restore_rollback_executed"

    # Database health
    DB_HEALTH_CHECK = "db.health_check"
    DB_HEALTH_CHECK_FAILED = "db.health_check_failed"
    DB_INTEGRITY_FAILED = "db.integrity_failed"
    DB_PERFORMANCE_DEGRADED = "db.performance_degraded"
    DB_SIZE_WARNING = "db.size_warning"
    DB_MIGRATION_PENDING = "db.migration_pending"
    DB_CONNECTION_FAILED = "db.connection_failed"
