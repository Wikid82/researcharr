"""Service Container for Dependency Injection.

Provides a lightweight dependency injection container that supports:
- Service registration and resolution
- Factory functions and singleton instances
- Interface-based service registration
- Circular dependency detection
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

LOGGER = logging.getLogger(__name__)


class ServiceContainer:
    """Lightweight dependency injection container.

    Supports registration of services as:
    - Singleton instances
    - Factory functions
    - Class constructors
    - Interface implementations
    """

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._resolving: set = set()

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance."""
        with self._lock:
            self._singletons[name] = instance
            LOGGER.debug("Registered singleton service: %s", name)

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory function that creates new instances."""
        with self._lock:
            self._factories[name] = factory
            LOGGER.debug("Registered factory service: %s", name)

    def register_class(self, name: str, cls: type[T], singleton: bool = True) -> None:
        """Register a class constructor, optionally as singleton."""

        def factory():
            return cls()

        if singleton:
            # Create singleton on first access
            def singleton_factory():
                if name not in self._singletons:
                    self._singletons[name] = factory()
                return self._singletons[name]

            self._factories[name] = singleton_factory
        else:
            self._factories[name] = factory

        LOGGER.debug("Registered class service: %s (singleton=%s)", name, singleton)

    def register_interface(self, interface_name: str, implementation_name: str) -> None:
        """Register an interface to implementation mapping."""

        def interface_factory():
            return self.resolve(implementation_name)

        self._factories[interface_name] = interface_factory
        LOGGER.debug("Registered interface: %s -> %s", interface_name, implementation_name)

    def resolve(self, name: str) -> Any:
        """Resolve a service by name."""
        with self._lock:
            # Check for circular dependencies
            if name in self._resolving:
                raise RuntimeError(f"Circular dependency detected resolving service: {name}")

            # Check singletons first
            if name in self._singletons:
                return self._singletons[name]

            # Try factory functions
            if name in self._factories:
                self._resolving.add(name)
                try:
                    service = self._factories[name]()
                    LOGGER.debug("Resolved service: %s", name)
                    return service
                finally:
                    self._resolving.discard(name)

            # Service not found
            raise KeyError(f"Service not registered: {name}")

    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return name in self._singletons or name in self._factories

    def list_services(self) -> dict[str, str]:
        """List all registered services and their types."""
        with self._lock:
            services = dict.fromkeys(self._singletons, "singleton")
            for name in self._factories:
                if name not in services:  # Don't override singleton type
                    services[name] = "factory"
            return services

    def clear(self) -> None:
        """Clear all registered services (mainly for testing)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self._resolving.clear()
            LOGGER.debug("Cleared all services")


# Global container instance for application use
_container: ServiceContainer | None = None
_container_lock = threading.Lock()


def get_container() -> ServiceContainer:
    """Get the global service container instance."""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """Reset the global container (mainly for testing)."""
    global _container
    with _container_lock:
        _container = None


# Convenience functions for common operations
def register_singleton(name: str, instance: Any) -> None:
    """Register a singleton in the global container."""
    get_container().register_singleton(name, instance)


def register_factory(name: str, factory: Callable[[], Any]) -> None:
    """Register a factory in the global container."""
    get_container().register_factory(name, factory)


def register_class(name: str, cls: type[T], singleton: bool = True) -> None:
    """Register a class in the global container."""
    get_container().register_class(name, cls, singleton)


def resolve(name: str) -> Any:
    """Resolve a service from the global container."""
    return get_container().resolve(name)


def has_service(name: str) -> bool:
    """Check if service exists in global container."""
    return get_container().has_service(name)
