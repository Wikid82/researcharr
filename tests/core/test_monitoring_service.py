"""Tests for MonitoringService."""

from unittest.mock import MagicMock, patch

from researcharr.core.services import MonitoringService


class TestMonitoringService:
    """Test suite for MonitoringService."""

    def test_init(self):
        """Test service initialization."""
        config = {"backups": {"retain_count": 10}}
        service = MonitoringService(config)

        assert service.config == config
        assert service._backup_monitor is None
        assert service._database_monitor is None

    def test_init_no_config(self):
        """Test initialization without config."""
        service = MonitoringService()

        assert service.config == {}

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_initialize_success(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test successful initialization."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        config = {"backups": {"retain_count": 5}}
        service = MonitoringService(config)

        # Setup mocks
        mock_backup_instance = MagicMock()
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_get_db_monitor.return_value = mock_db_instance

        # Initialize
        result = service.initialize()

        assert result is True
        assert service._backup_monitor is not None
        assert service._database_monitor is not None

        # Verify backup monitor creation
        mock_backup_monitor.assert_called_once()
        call_args = mock_backup_monitor.call_args
        assert call_args[0][0].endswith("/backups")  # backups_dir
        assert call_args[0][1] == {"retain_count": 5}  # config

    @patch("researcharr.monitoring.BackupHealthMonitor")
    def test_initialize_failure(self, mock_backup_monitor):
        """Test initialization failure."""
        mock_backup_monitor.side_effect = Exception("Init failed")

        service = MonitoringService()
        result = service.initialize()

        assert result is False
        assert service._backup_monitor is None

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_check_all_health_success(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test successful health check."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks
        mock_backup_instance = MagicMock()
        mock_backup_instance.check_backup_health.return_value = {
            "status": "ok",
            "alerts": [],
        }
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.check_database_health.return_value = {
            "status": "ok",
            "alerts": [],
        }
        mock_get_db_monitor.return_value = mock_db_instance

        # Check health
        result = service.check_all_health()

        assert result["status"] == "ok"
        assert result["backups"]["status"] == "ok"
        assert result["database"]["status"] == "ok"
        assert len(result["alerts"]) == 0

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_check_all_health_with_warnings(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test health check with warnings."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks with warnings
        mock_backup_instance = MagicMock()
        mock_backup_instance.check_backup_health.return_value = {
            "status": "warning",
            "alerts": [{"level": "warning", "message": "Old backup"}],
        }
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.check_database_health.return_value = {
            "status": "ok",
            "alerts": [],
        }
        mock_get_db_monitor.return_value = mock_db_instance

        # Check health
        result = service.check_all_health()

        assert result["status"] == "warning"
        assert result["backups"]["status"] == "warning"
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["source"] == "backups"

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_check_all_health_with_errors(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test health check with errors."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks with errors
        mock_backup_instance = MagicMock()
        mock_backup_instance.check_backup_health.return_value = {
            "status": "ok",
            "alerts": [],
        }
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.check_database_health.return_value = {
            "status": "error",
            "alerts": [{"level": "error", "message": "Connection failed"}],
        }
        mock_get_db_monitor.return_value = mock_db_instance

        # Check health
        result = service.check_all_health()

        assert result["status"] == "error"
        assert result["database"]["status"] == "error"
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["source"] == "database"

    def test_check_all_health_not_initialized(self):
        """Test health check initializes monitors if needed."""
        service = MonitoringService()

        # Mock initialize to fail
        with patch.object(service, "initialize", return_value=False):
            result = service.check_all_health()

            assert result["status"] == "error"
            assert len(result["alerts"]) == 1
            assert "not initialized" in result["alerts"][0]["message"]

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_check_all_health_handles_exceptions(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test health check handles monitor exceptions."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks
        mock_backup_instance = MagicMock()
        mock_backup_instance.check_backup_health.side_effect = Exception("Backup error")
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.check_database_health.return_value = {
            "status": "ok",
            "alerts": [],
        }
        mock_get_db_monitor.return_value = mock_db_instance

        # Check health
        result = service.check_all_health()

        assert result["backups"]["status"] == "error"
        assert "Backup error" in result["backups"]["error"]

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_get_all_metrics_success(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test getting metrics from all monitors."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks
        mock_backup_instance = MagicMock()
        mock_backup_instance.get_metrics.return_value = {"total_backups": 5}
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.get_metrics.return_value = {"db_size": 1024}
        mock_get_db_monitor.return_value = mock_db_instance

        # Get metrics
        metrics = service.get_all_metrics()

        assert metrics["backups"]["total_backups"] == 5
        assert metrics["database"]["db_size"] == 1024

    def test_get_all_metrics_not_initialized(self):
        """Test get_all_metrics initializes monitors if needed."""
        service = MonitoringService()

        # Should initialize monitors automatically
        with patch.object(service, "initialize", return_value=True):
            metrics = service.get_all_metrics()

            assert "backups" in metrics
            assert "database" in metrics

    @patch("os.getenv")
    @patch("researcharr.core.events.get_event_bus")
    @patch("researcharr.monitoring.BackupHealthMonitor")
    @patch("researcharr.monitoring.get_database_health_monitor")
    def test_get_all_metrics_handles_exceptions(
        self, mock_get_db_monitor, mock_backup_monitor, mock_event_bus, mock_getenv
    ):
        """Test get_all_metrics handles monitor exceptions."""
        mock_getenv.return_value = "/config"
        mock_event_bus.return_value = MagicMock()

        service = MonitoringService()

        # Setup mocks
        mock_backup_instance = MagicMock()
        mock_backup_instance.get_metrics.side_effect = Exception("Metrics error")
        mock_backup_monitor.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_instance.get_metrics.return_value = {"db_size": 2048}
        mock_get_db_monitor.return_value = mock_db_instance

        # Get metrics - should not raise, just log warning
        metrics = service.get_all_metrics()

        # Backup metrics should be empty due to exception
        assert metrics["backups"] == {}
        # Database metrics should succeed
        assert metrics["database"]["db_size"] == 2048
