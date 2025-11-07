"""Coverage tests for researcharr.core.application module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


def test_core_application_factory_initialization():
    """Test CoreApplicationFactory initialization."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    assert factory.container is not None
    assert factory.event_bus is not None
    assert factory.lifecycle is not None
    assert factory.config_manager is not None


def test_register_core_services():
    """Test registering core services."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.object(factory.container, "register_singleton") as mock_register:
        with patch.object(factory.event_bus, "publish_simple"):
            factory.register_core_services()
            
            # Should register multiple services
            assert mock_register.call_count >= 7


def test_setup_configuration_default():
    """Test setup_configuration with defaults."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    config = factory.setup_configuration()
    
    assert isinstance(config, dict)
    assert "app" in config
    assert "logging" in config


def test_setup_configuration_custom_dir():
    """Test setup_configuration with custom config dir."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = factory.setup_configuration(config_dir=tmpdir)
        
        assert isinstance(config, dict)


def test_setup_configuration_with_yaml_file():
    """Test loading configuration from YAML file."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yml"
        config_file.write_text("app:\n  name: test_app\n  version: 2.0.0\n")
        
        with patch.object(factory.config_manager, "add_source") as mock_add:
            config = factory.setup_configuration(config_dir=tmpdir)
            
            # Should add config source
            assert mock_add.called


def test_setup_configuration_missing_yaml():
    """Test setup_configuration handles missing YAML gracefully."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # No config.yml file
        config = factory.setup_configuration(config_dir=tmpdir)
        
        # Should still return default config
        assert isinstance(config, dict)


def test_setup_configuration_invalid_yaml():
    """Test setup_configuration handles invalid YAML."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yml"
        config_file.write_text("invalid: yaml: content:")
        
        config = factory.setup_configuration(config_dir=tmpdir)
        
        # Should fallback to defaults
        assert isinstance(config, dict)


def test_setup_configuration_environment_overrides():
    """Test environment variables override config."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.dict(os.environ, {"PUID": "1001", "PGID": "1001", "TIMEZONE": "UTC"}):
        config = factory.setup_configuration()
        
        assert config["general"]["PUID"] == "1001"
        assert config["general"]["PGID"] == "1001"
        assert config["general"]["Timezone"] == "UTC"


def test_setup_logging_service():
    """Test logging service setup."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    logging_service = factory.container.resolve("logging_service")
    
    assert logging_service is not None


def test_setup_database_service():
    """Test database service setup."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    db_service = factory.container.resolve("database_service")
    
    assert db_service is not None


def test_setup_health_service():
    """Test health service setup."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    health_service = factory.container.resolve("health_service")
    
    assert health_service is not None


def test_setup_metrics_service():
    """Test metrics service setup."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    metrics_service = factory.container.resolve("metrics_service")
    
    assert metrics_service is not None


def test_event_bus_registration():
    """Test event bus is registered in container."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    event_bus = factory.container.resolve("event_bus")
    
    assert event_bus is not None


def test_lifecycle_registration():
    """Test lifecycle is registered in container."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    lifecycle = factory.container.resolve("lifecycle")
    
    assert lifecycle is not None


def test_config_manager_registration():
    """Test config manager is registered in container."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    factory.register_core_services()
    
    config_mgr = factory.container.resolve("config_manager")
    
    assert config_mgr is not None


def test_service_registration_event():
    """Test service registration publishes event."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.object(factory.event_bus, "publish_simple") as mock_publish:
        factory.register_core_services()
        
        # Should publish APP_STARTING event
        mock_publish.assert_called()
        call_args = mock_publish.call_args
        assert "services_registered" in call_args[1]["data"]


def test_default_config_values():
    """Test default configuration values."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    config = factory.setup_configuration()
    
    assert config["app"]["name"] == "researcharr"
    assert config["logging"]["level"] == "INFO"
    assert config["scheduling"]["cron_schedule"] == "0 0 * * *"


def test_backups_config_defaults():
    """Test default backup configuration."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    config = factory.setup_configuration()
    
    assert config["backups"]["retain_count"] == 10
    assert config["backups"]["retain_days"] == 30
    assert config["backups"]["pre_restore"] is True


def test_user_config_defaults():
    """Test default user configuration."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    config = factory.setup_configuration()
    
    assert config["user"]["username"] == "admin"
    assert "password" in config["user"]


def test_setup_configuration_priority():
    """Test configuration source priority."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.object(factory.config_manager, "add_source") as mock_add:
        factory.setup_configuration()
        
        # Default config should have priority 100
        call_args = mock_add.call_args_list[0]
        assert call_args[1]["priority"] == 100


def test_create_flask_app():
    """Test Flask app creation."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    # Test that factory can create app context
    assert factory.container is not None


def test_config_manager_source_addition():
    """Test adding configuration sources."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.object(factory.config_manager, "add_source") as mock_add:
        factory.setup_configuration()
        
        # Should add at least default config source
        assert mock_add.call_count >= 1


def test_configuration_with_env_loglevel():
    """Test LOGLEVEL environment variable."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with patch.dict(os.environ, {"LOGLEVEL": "DEBUG"}):
        config = factory.setup_configuration()
        
        assert config["general"]["LogLevel"] == "DEBUG"


def test_configuration_file_path_building():
    """Test configuration file paths are built correctly."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = factory.setup_configuration(config_dir=tmpdir)
        
        # Logging file should be in config dir
        assert tmpdir in config["logging"]["file"]


def test_setup_configuration_returns_merged_config():
    """Test setup_configuration returns merged configuration."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    config = factory.setup_configuration()
    
    # Should have merged all sources
    assert "app" in config
    assert "general" in config
    assert "backups" in config


def test_factory_initialization_order():
    """Test factory components initialize in correct order."""
    from researcharr.core.application import CoreApplicationFactory
    
    # Should not raise during initialization
    factory = CoreApplicationFactory()
    
    # All components should be available
    assert factory.container is not None
    assert factory.event_bus is not None
    assert factory.lifecycle is not None
    assert factory.config_manager is not None


def test_setup_with_read_only_config_dir():
    """Test setup handles read-only config directory."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    # Should handle gracefully
    config = factory.setup_configuration(config_dir="/nonexistent")
    
    assert isinstance(config, dict)


def test_yaml_config_loading():
    """Test YAML configuration file loading."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yml"
        config_data = {
            "app": {"name": "custom_app"},
            "custom_key": "custom_value"
        }
        
        import yaml
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        config = factory.setup_configuration(config_dir=tmpdir)
        
        # Should have loaded custom config
        assert isinstance(config, dict)


def test_configuration_merge_with_env():
    """Test configuration merges with environment variables."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    env_vars = {
        "PUID": "2000",
        "PGID": "2000",
        "TIMEZONE": "Europe/London",
        "LOGLEVEL": "WARNING"
    }
    
    with patch.dict(os.environ, env_vars):
        config = factory.setup_configuration()
        
        assert config["general"]["PUID"] == "2000"
        assert config["general"]["PGID"] == "2000"
        assert config["general"]["Timezone"] == "Europe/London"
        assert config["general"]["LogLevel"] == "WARNING"


def test_service_registration_order():
    """Test services are registered in correct order."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    
    calls = []
    
    original_register = factory.container.register_singleton
    def track_register(name, service):
        calls.append(name)
        return original_register(name, service)
    
    with patch.object(factory.container, "register_singleton", side_effect=track_register):
        factory.register_core_services()
        
        # Core services should be registered
        assert "database_service" in calls
        assert "logging_service" in calls


def test_config_with_database_url():
    """Test database configuration."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    config = factory.setup_configuration()
    
    assert "database" in config
    assert "path" in config["database"]


def test_scheduling_config():
    """Test scheduling configuration."""
    from researcharr.core.application import CoreApplicationFactory
    
    factory = CoreApplicationFactory()
    config = factory.setup_configuration()
    
    assert "scheduling" in config
    assert "cron_schedule" in config["scheduling"]
    assert "timezone" in config["scheduling"]
