"""Integration tests for service orchestration.

Tests the interaction between SchedulerService, MonitoringService, and StorageService
to ensure they work together correctly in a production-like environment.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from researcharr.core import (
    MonitoringService,
    SchedulerService,
    StorageService,
    get_container,
)
from researcharr.core.application import CoreApplicationFactory


class TestServiceIntegration:
    """Test integration between core services."""

    def test_scheduler_monitoring_integration(self):
        """Test that scheduler and monitoring services work together."""
        # Create services with config
        config = {
            "scheduling": {"timezone": "UTC"},
            "backups": {"retain_count": 5},
            "database": {"monitoring": {"enabled": True}},
        }

        scheduler_service = SchedulerService(config)
        monitoring_service = MonitoringService(config)

        # Verify services can be initialized
        assert scheduler_service.initialize()
        assert monitoring_service.initialize()

        # Verify scheduler can be started
        assert scheduler_service.start()
        assert scheduler_service.is_running()

        # Get schedule info
        schedule_info = scheduler_service.get_schedule_info()
        assert "scheduler_running" in schedule_info
        assert schedule_info["scheduler_running"] is True

        # Get monitoring metrics
        metrics = monitoring_service.get_all_metrics()
        assert "backups" in metrics
        assert "database" in metrics

        # Stop scheduler
        scheduler_service.stop()
        assert not scheduler_service.is_running()

    def test_storage_service_integration(self):
        """Test storage service with repository layer."""
        storage_service = StorageService()

        # Initialize storage
        assert storage_service.initialize()

        # Create a unit of work
        uow = storage_service.create_unit_of_work()
        assert uow is not None

    def test_application_factory_integration(self):
        """Test that application factory registers all services correctly."""
        factory = CoreApplicationFactory()

        # Register services
        factory.register_core_services()

        # Verify all services are registered
        container = get_container()
        assert container.resolve("database_service") is not None
        assert container.resolve("logging_service") is not None
        assert container.resolve("health_service") is not None
        assert container.resolve("metrics_service") is not None
        assert container.resolve("scheduler_service") is not None
        assert container.resolve("monitoring_service") is not None
        assert container.resolve("storage_service") is not None

        # Clean up
        container._services.clear()
        container._singletons.clear()

    @pytest.mark.skipif(not Path("/tmp").exists(), reason="Requires /tmp directory for temp DB")
    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow with real database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create a minimal SQLite database
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.commit()
            conn.close()

            # Create monitoring service with real database
            config = {
                "database": {
                    "monitoring": {
                        "enabled": True,
                        "health_check_interval": 300,
                    }
                }
            }

            monitoring_service = MonitoringService(config)
            monitoring_service.initialize()

            # Run health checks
            health = monitoring_service.check_all_health()

            # Verify health check structure
            assert "status" in health
            assert "backups" in health
            assert "database" in health
            assert "alerts" in health

            # Get metrics
            metrics = monitoring_service.get_all_metrics()
            assert "backups" in metrics
            assert "database" in metrics

    def test_scheduler_lifecycle_integration(self):
        """Test scheduler lifecycle with application lifecycle hooks."""
        config = {"scheduling": {"timezone": "UTC"}}

        # Create scheduler
        scheduler_service = SchedulerService(config)

        # Simulate application startup
        assert scheduler_service.initialize()
        assert scheduler_service.start()
        assert scheduler_service.is_running()

        # Get schedule info
        info = scheduler_service.get_schedule_info()
        assert info["scheduler_running"] is True

        # Simulate application shutdown
        scheduler_service.stop()
        assert not scheduler_service.is_running()

        # Verify clean shutdown
        final_info = scheduler_service.get_schedule_info()
        assert final_info["scheduler_running"] is False

    def test_monitoring_aggregation(self):
        """Test that monitoring service aggregates alerts correctly."""
        config = {}
        monitoring_service = MonitoringService(config)

        # Mock the monitors to return specific statuses
        with patch.object(monitoring_service, "initialize", return_value=True):
            mock_backup_monitor = Mock()
            mock_backup_monitor.check_backup_health.return_value = {
                "status": "warning",
                "alerts": [
                    {"level": "warning", "message": "Backup is old"},
                ],
            }

            mock_db_monitor = Mock()
            mock_db_monitor.check_database_health.return_value = {
                "status": "ok",
                "alerts": [],
            }

            monitoring_service._backup_monitor = mock_backup_monitor
            monitoring_service._database_monitor = mock_db_monitor

            # Check aggregated health
            health = monitoring_service.check_all_health()

            # Verify aggregation
            assert health["status"] == "warning"  # Worst status wins
            assert len(health["alerts"]) == 1  # One alert from backups
            assert health["alerts"][0]["source"] == "backups"

    def test_storage_transaction_rollback(self):
        """Test that storage service properly handles transaction rollback."""
        storage_service = StorageService()
        storage_service.initialize()

        # Create a mock UnitOfWork that raises an exception
        with patch("researcharr.repositories.uow.UnitOfWork") as mock_uow_class:
            mock_uow = Mock()
            mock_uow.__enter__ = Mock(return_value=mock_uow)
            mock_uow.__exit__ = Mock(return_value=None)
            mock_uow.apps.get_all.side_effect = Exception("Database error")
            mock_uow_class.return_value = mock_uow

            # This should raise but not crash the application
            with pytest.raises(Exception, match="Database error"):
                storage_service.get_all_apps()

            # Verify __exit__ was called (transaction handled)
            mock_uow.__exit__.assert_called_once()


class TestServiceDependencies:
    """Test service dependency management."""

    def test_scheduler_depends_on_config(self):
        """Test that scheduler service uses configuration correctly."""
        config = {"scheduling": {"timezone": "America/New_York"}}
        service = SchedulerService(config)

        assert service.config == config
        assert service.config["scheduling"]["timezone"] == "America/New_York"

    def test_monitoring_depends_on_config(self):
        """Test that monitoring service uses configuration correctly."""
        config = {
            "backups": {"retain_count": 10},
            "database": {"monitoring": {"enabled": True}},
        }
        service = MonitoringService(config)

        assert service.config == config

    def test_services_are_singletons(self):
        """Test that services are properly registered as singletons."""
        factory = CoreApplicationFactory()
        factory.register_core_services()

        container = get_container()

        # Get services twice
        scheduler1 = container.resolve("scheduler_service")
        scheduler2 = container.resolve("scheduler_service")

        # Should be the same instance
        assert scheduler1 is scheduler2

        monitoring1 = container.resolve("monitoring_service")
        monitoring2 = container.resolve("monitoring_service")

        assert monitoring1 is monitoring2

        # Clean up
        container._services.clear()
        container._singletons.clear()


class TestErrorHandling:
    """Test error handling in integrated services."""

    def test_scheduler_handles_initialization_failure(self):
        """Test scheduler handles initialization failure gracefully."""
        with patch(
            "apscheduler.schedulers.background.BackgroundScheduler",
            side_effect=Exception("Scheduler init failed"),
        ):
            service = SchedulerService()
            result = service.initialize()

            assert result is False
            assert service._scheduler is None

    def test_monitoring_handles_initialization_failure(self):
        """Test monitoring handles initialization failure gracefully."""
        with patch(
            "researcharr.monitoring.BackupHealthMonitor",
            side_effect=Exception("Monitor init failed"),
        ):
            service = MonitoringService()
            result = service.initialize()

            assert result is False

    def test_storage_handles_missing_uow(self):
        """Test storage service handles missing UnitOfWork gracefully."""
        service = StorageService()

        # Patch the UnitOfWork import to raise an ImportError
        with patch.object(service, "create_unit_of_work", side_effect=ImportError("No module")):
            # Attempting to create UoW should raise
            with pytest.raises(ImportError):
                service.create_unit_of_work()
