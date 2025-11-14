"""Tests for SchedulerService."""

from unittest.mock import MagicMock, patch

from researcharr.core.services import SchedulerService


class TestSchedulerService:
    """Test suite for SchedulerService."""

    def test_init(self):
        """Test service initialization."""
        config = {"scheduling": {"timezone": "America/New_York"}}
        service = SchedulerService(config)

        assert service.config == config
        assert service._scheduler is None
        assert service._backup_scheduler is None
        assert service._database_scheduler is None
        assert service._started is False

    def test_init_no_config(self):
        """Test initialization without config."""
        service = SchedulerService()

        assert service.config == {}
        assert not service.is_running()

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    @patch("researcharr.scheduling.BackupSchedulerService")
    @patch("researcharr.scheduling.DatabaseSchedulerService")
    def test_initialize_success(self, mock_db_scheduler, mock_backup_scheduler, mock_bg_scheduler):
        """Test successful initialization."""
        config = {"scheduling": {"timezone": "UTC"}}
        service = SchedulerService(config)

        # Setup mocks
        mock_scheduler_instance = MagicMock()
        mock_bg_scheduler.return_value = mock_scheduler_instance

        # Initialize
        result = service.initialize()

        assert result is True
        assert service._scheduler is not None
        mock_bg_scheduler.assert_called_once_with(timezone="UTC")
        mock_backup_scheduler.assert_called_once_with(mock_scheduler_instance, config)
        mock_db_scheduler.assert_called_once_with(mock_scheduler_instance, config)

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_initialize_failure(self, mock_bg_scheduler):
        """Test initialization failure."""
        mock_bg_scheduler.side_effect = Exception("Init failed")

        service = SchedulerService()
        result = service.initialize()

        assert result is False
        assert service._scheduler is None

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    @patch("researcharr.scheduling.BackupSchedulerService")
    @patch("researcharr.scheduling.DatabaseSchedulerService")
    @patch("researcharr.core.services.get_event_bus")
    def test_start_success(
        self, mock_event_bus, mock_db_scheduler, mock_backup_scheduler, mock_bg_scheduler
    ):
        """Test successful scheduler start."""
        service = SchedulerService()

        # Setup mocks
        mock_scheduler_instance = MagicMock()
        mock_bg_scheduler.return_value = mock_scheduler_instance

        mock_backup_instance = MagicMock()
        mock_backup_scheduler.return_value = mock_backup_instance

        mock_db_instance = MagicMock()
        mock_db_scheduler.return_value = mock_db_instance

        mock_bus = MagicMock()
        mock_event_bus.return_value = mock_bus

        # Start
        result = service.start()

        assert result is True
        assert service.is_running()

        # Verify setup calls
        mock_backup_instance.setup.assert_called_once()
        mock_db_instance.setup.assert_called_once()
        mock_scheduler_instance.start.assert_called_once()

        # Verify event published
        mock_bus.publish_simple.assert_called_once()

    def test_start_already_running(self):
        """Test starting when already running."""
        service = SchedulerService()
        service._started = True

        result = service.start()

        assert result is True

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_start_failure(self, mock_bg_scheduler):
        """Test start failure."""
        mock_bg_scheduler.side_effect = Exception("Start failed")

        service = SchedulerService()
        result = service.start()

        assert result is False
        assert not service.is_running()

    @patch("researcharr.core.services.get_event_bus")
    def test_stop_success(self, mock_event_bus):
        """Test successful scheduler stop."""
        service = SchedulerService()
        service._started = True

        # Setup mocks
        mock_scheduler = MagicMock()
        service._scheduler = mock_scheduler

        mock_backup = MagicMock()
        service._backup_scheduler = mock_backup

        mock_db = MagicMock()
        service._database_scheduler = mock_db

        mock_bus = MagicMock()
        mock_event_bus.return_value = mock_bus

        # Stop
        service.stop()

        assert not service.is_running()

        # Verify cleanup calls
        mock_backup.remove_jobs.assert_called_once()
        mock_db.remove_jobs.assert_called_once()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)

        # Verify event published
        mock_bus.publish_simple.assert_called_once()

    def test_stop_not_running(self):
        """Test stop when not running."""
        service = SchedulerService()

        # Should not raise exception
        service.stop()

        assert not service.is_running()

    def test_stop_with_error(self):
        """Test stop handles errors gracefully."""
        service = SchedulerService()
        service._started = True

        mock_scheduler = MagicMock()
        mock_scheduler.shutdown.side_effect = Exception("Shutdown failed")
        service._scheduler = mock_scheduler

        # Should not raise exception
        service.stop()

    def test_is_running(self):
        """Test is_running status."""
        service = SchedulerService()

        assert not service.is_running()

        service._started = True
        service._scheduler = MagicMock()

        assert service.is_running()

    def test_get_schedule_info_not_initialized(self):
        """Test getting schedule info when not initialized."""
        service = SchedulerService()

        info = service.get_schedule_info()

        assert info["scheduler_running"] is False
        assert info["backups"] == {}
        assert info["database"] == {}

    def test_get_schedule_info_with_schedulers(self):
        """Test getting schedule info with schedulers."""
        service = SchedulerService()
        service._started = True
        service._scheduler = MagicMock()

        # Setup mock schedulers
        mock_backup = MagicMock()
        mock_backup.get_schedule_info.return_value = {"enabled": True}
        service._backup_scheduler = mock_backup

        mock_db = MagicMock()
        mock_db.get_schedule_info.return_value = {"enabled": True, "interval": 300}
        service._database_scheduler = mock_db

        # Get info
        info = service.get_schedule_info()

        assert info["scheduler_running"] is True
        assert info["backups"] == {"enabled": True}
        assert info["database"] == {"enabled": True, "interval": 300}
