"""Tests for StorageService."""

from unittest.mock import Mock, patch

from researcharr.core.services import StorageService


class TestStorageService:
    """Test suite for StorageService."""

    def test_init(self):
        """Test service initialization."""
        service = StorageService()
        assert service._initialized is False

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_initialize_success(self, mock_uow):
        """Test successful initialization."""
        service = StorageService()
        result = service.initialize()

        assert result is True
        assert service._initialized is True

    def test_initialize_failure(self):
        """Test initialization failure."""
        # Mock the import to raise an exception
        with patch("researcharr.core.services.StorageService.initialize") as mock_init:
            mock_init.return_value = False
            result = mock_init()

            assert result is False

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_create_unit_of_work(self, mock_uow_class):
        """Test creating a unit of work."""
        service = StorageService()
        service._initialized = True

        mock_uow_instance = Mock()
        mock_uow_class.return_value = mock_uow_instance

        uow = service.create_unit_of_work()

        assert uow == mock_uow_instance
        mock_uow_class.assert_called_once()

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_create_unit_of_work_auto_initialize(self, mock_uow_class):
        """Test creating a unit of work auto-initializes."""
        service = StorageService()

        mock_uow_instance = Mock()
        mock_uow_class.return_value = mock_uow_instance

        uow = service.create_unit_of_work()

        assert service._initialized is True
        assert uow == mock_uow_instance

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_app(self, mock_uow_class):
        """Test getting an app by ID."""
        service = StorageService()

        mock_app = Mock(id=1, name="Test App")
        mock_uow = Mock()
        mock_uow.apps.get_by_id.return_value = mock_app
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_app(1)

        assert result == mock_app
        mock_uow.apps.get_by_id.assert_called_once_with(1)

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_all_apps(self, mock_uow_class):
        """Test getting all apps."""
        service = StorageService()

        mock_apps = [Mock(id=1), Mock(id=2)]
        mock_uow = Mock()
        mock_uow.apps.get_all.return_value = mock_apps
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_all_apps()

        assert result == mock_apps
        mock_uow.apps.get_all.assert_called_once()

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_enabled_apps(self, mock_uow_class):
        """Test getting enabled apps."""
        service = StorageService()

        mock_apps = [Mock(id=1, enabled=True)]
        mock_uow = Mock()
        mock_uow.apps.get_enabled.return_value = mock_apps
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_enabled_apps()

        assert result == mock_apps
        mock_uow.apps.get_enabled.assert_called_once()

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_tracked_item(self, mock_uow_class):
        """Test getting a tracked item by ID."""
        service = StorageService()

        mock_item = Mock(id=1, title="Test Item")
        mock_uow = Mock()
        mock_uow.items.get_by_id.return_value = mock_item
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_tracked_item(1)

        assert result == mock_item
        mock_uow.items.get_by_id.assert_called_once_with(1)

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_processing_logs(self, mock_uow_class):
        """Test getting processing logs."""
        service = StorageService()

        mock_logs = [Mock(id=1), Mock(id=2)]
        mock_uow = Mock()
        mock_uow.logs.get_recent.return_value = mock_logs
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_processing_logs(limit=50)

        assert result == mock_logs
        mock_uow.logs.get_recent.assert_called_once_with(limit=50)

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_processing_logs_default_limit(self, mock_uow_class):
        """Test getting processing logs with default limit."""
        service = StorageService()

        mock_logs = [Mock(id=1)]
        mock_uow = Mock()
        mock_uow.logs.get_recent.return_value = mock_logs
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_processing_logs()

        assert result == mock_logs
        mock_uow.logs.get_recent.assert_called_once_with(limit=100)

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_search_cycle(self, mock_uow_class):
        """Test getting a search cycle by ID."""
        service = StorageService()

        mock_cycle = Mock(id=1)
        mock_uow = Mock()
        mock_uow.cycles.get_by_id.return_value = mock_cycle
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_search_cycle(1)

        assert result == mock_cycle
        mock_uow.cycles.get_by_id.assert_called_once_with(1)

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_setting(self, mock_uow_class):
        """Test getting a setting."""
        service = StorageService()

        mock_setting = Mock(value="test_value")
        mock_uow = Mock()
        mock_uow.settings.get_by_key.return_value = mock_setting
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_setting("test_key")

        assert result == "test_value"
        mock_uow.settings.get_by_key.assert_called_once_with("test_key")

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_get_setting_not_found(self, mock_uow_class):
        """Test getting a setting that doesn't exist."""
        service = StorageService()

        mock_uow = Mock()
        mock_uow.settings.get_by_key.return_value = None
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        result = service.get_setting("missing_key", default="default_value")

        assert result == "default_value"
        mock_uow.settings.get_by_key.assert_called_once_with("missing_key")

    @patch("researcharr.repositories.uow.UnitOfWork")
    def test_set_setting(self, mock_uow_class):
        """Test setting a value."""
        service = StorageService()

        mock_uow = Mock()
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        service.set_setting("test_key", "test_value")

        mock_uow.settings.set.assert_called_once_with("test_key", "test_value")
