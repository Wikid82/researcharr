"""Tests for the core service container implementation."""

import unittest

from researcharr.core.container import ServiceContainer


class TestServiceContainer(unittest.TestCase):
    """Test the service container implementation."""

    def setUp(self):
        """Set up test environment."""
        self.container = ServiceContainer()

    def test_singleton_registration(self):
        """Test singleton service registration."""

        class TestService:
            def __init__(self):
                self.value = "test"

        instance = TestService()

        # Register singleton instance
        self.container.register_singleton("test_service", instance)

        # Get service instances
        service1 = self.container.resolve("test_service")
        service2 = self.container.resolve("test_service")

        # Should be the same instance
        self.assertIs(service1, service2)
        self.assertIs(service1, instance)
        self.assertEqual(service1.value, "test")

    def test_factory_registration(self):
        """Test factory service registration."""

        class TestService:
            def __init__(self):
                self.value = "test"

        # Register factory
        self.container.register_factory("test_service", TestService)

        # Get service instances
        service1 = self.container.resolve("test_service")
        service2 = self.container.resolve("test_service")

        # Should be different instances
        self.assertIsNot(service1, service2)
        self.assertEqual(service1.value, "test")
        self.assertEqual(service2.value, "test")

    def test_class_registration_singleton(self):
        """Test class registration as singleton."""

        class TestService:
            def __init__(self):
                self.value = "test"

        # Register class as singleton (default)
        self.container.register_class("test_service", TestService, singleton=True)

        # Get service instances
        service1 = self.container.resolve("test_service")
        service2 = self.container.resolve("test_service")

        # Should be the same instance
        self.assertIs(service1, service2)
        self.assertEqual(service1.value, "test")

    def test_class_registration_factory(self):
        """Test class registration as factory."""

        class TestService:
            def __init__(self):
                self.value = "test"

        # Register class as factory
        self.container.register_class("test_service", TestService, singleton=False)

        # Get service instances
        service1 = self.container.resolve("test_service")
        service2 = self.container.resolve("test_service")

        # Should be different instances
        self.assertIsNot(service1, service2)
        self.assertEqual(service1.value, "test")
        self.assertEqual(service2.value, "test")

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""

        # Create circular dependency by making factories that reference each other
        def factory_a():
            # This will try to resolve service_b, creating a circular dependency
            self.container.resolve("service_b")
            return "ServiceA"

        def factory_b():
            # This will try to resolve service_a, creating a circular dependency
            self.container.resolve("service_a")
            return "ServiceB"

        # Register services
        self.container.register_factory("service_a", factory_a)
        self.container.register_factory("service_b", factory_b)

        # Should detect circular dependency when trying to resolve either service
        with self.assertRaises(RuntimeError):
            self.container.resolve("service_a")

    def test_service_not_found(self):
        """Test behavior when service is not found."""

        with self.assertRaises(KeyError):
            self.container.resolve("nonexistent_service")

    def test_has_service(self):
        """Test service existence check."""

        class TestService:
            pass

        # Should not exist initially
        self.assertFalse(self.container.has_service("test_service"))

        # Register service
        self.container.register_class("test_service", TestService)

        # Should exist now
        self.assertTrue(self.container.has_service("test_service"))

    def test_list_services(self):
        """Test listing registered services."""

        class TestService1:
            pass

        class TestService2:
            pass

        instance = TestService1()

        # Initially empty
        self.assertEqual(len(self.container.list_services()), 0)

        # Register services
        self.container.register_singleton("service1", instance)
        self.container.register_factory("service2", TestService2)

        services = self.container.list_services()
        self.assertEqual(len(services), 2)
        self.assertIn("service1", services)
        self.assertIn("service2", services)
        self.assertEqual(services["service1"], "singleton")
        self.assertEqual(services["service2"], "factory")

    def test_clear_services(self):
        """Test clearing all services."""

        class TestService:
            pass

        # Register service
        self.container.register_class("test_service", TestService)
        self.assertEqual(len(self.container.list_services()), 1)

        # Clear services
        self.container.clear()
        self.assertEqual(len(self.container.list_services()), 0)

    def test_interface_registration(self):
        """Test interface to implementation mapping."""

        class DatabaseInterface:
            pass

        class SQLiteDatabase:
            def __init__(self):
                self.type = "sqlite"

        # Register implementation
        self.container.register_class("sqlite_db", SQLiteDatabase)

        # Register interface mapping
        self.container.register_interface("database", "sqlite_db")

        # Resolve via interface
        db = self.container.resolve("database")
        self.assertIsInstance(db, SQLiteDatabase)
        self.assertEqual(db.type, "sqlite")

    def test_lazy_singleton_initialization(self):
        """Test that singletons are initialized lazily."""

        initialization_count = 0

        class TestService:
            def __init__(self):
                nonlocal initialization_count
                initialization_count += 1

        # Register class as singleton
        self.container.register_class("test_service", TestService, singleton=True)

        # Should not be initialized yet
        self.assertEqual(initialization_count, 0)

        # Get service - should initialize now
        self.container.resolve("test_service")
        self.assertEqual(initialization_count, 1)

        # Get again - should not initialize again
        self.container.resolve("test_service")
        self.assertEqual(initialization_count, 1)

    def test_factory_multiple_instances(self):
        """Test that factories create new instances each time."""

        initialization_count = 0

        class TestService:
            def __init__(self):
                nonlocal initialization_count
                initialization_count += 1

        # Register class as factory
        self.container.register_class("test_service", TestService, singleton=False)

        # Should not be initialized yet
        self.assertEqual(initialization_count, 0)

        # Get service - should initialize
        self.container.resolve("test_service")
        self.assertEqual(initialization_count, 1)

        # Get again - should initialize again
        self.container.resolve("test_service")
        self.assertEqual(initialization_count, 2)


if __name__ == "__main__":
    unittest.main()
