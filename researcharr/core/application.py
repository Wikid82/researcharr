"""Core Application Factory.

This module provides the core application setup and configuration functionality
extracted from factory.py, integrated with the new core architecture components.
"""

import importlib.util
import logging
import os
from copy import deepcopy
from types import ModuleType
from typing import Any

import yaml
from werkzeug.security import generate_password_hash

from flask import Flask

from .config import get_config_manager
from .container import get_container
from .events import Events, get_event_bus
from .lifecycle import add_shutdown_hook, add_startup_hook, get_lifecycle
from .services import (
    ConnectivityService,
    DatabaseService,
    FileSystemService,
    HealthService,
    HttpClientService,
    LoggingService,
    MetricsService,
    MonitoringService,
    SchedulerService,
    StorageService,
)

LOGGER = logging.getLogger(__name__)

try:
    # Optional: repository Unit of Work registration
    from researcharr.repositories.uow import UnitOfWork  # type: ignore
except Exception:  # pragma: no cover - defensive import for optional module
    UnitOfWork = None  # type: ignore


class CoreApplicationFactory:
    """Factory for creating and configuring core application components."""

    def __init__(self):
        self.container = get_container()
        self.event_bus = get_event_bus()
        self.lifecycle = get_lifecycle()
        self.config_manager = get_config_manager()

    def register_core_services(self) -> None:
        """Register all core services in the container."""
        # Get configuration for service initialization
        # Note: config_manager stores config in _config dict
        config = self.config_manager._config if hasattr(self.config_manager, "_config") else {}

        # Get DB path from config or environment or use default
        db_path = (
            config.get("database", {}).get("path")
            or os.getenv("RESEARCHARR_DB")
            or "researcharr.db"
        )

        # Register infrastructure services first (no dependencies)
        self.container.register_singleton("filesystem_service", FileSystemService())
        self.container.register_singleton("http_client_service", HttpClientService())

        # Register core services with injected dependencies
        self.container.register_singleton("database_service", DatabaseService(db_path))
        self.container.register_singleton("logging_service", LoggingService())
        self.container.register_singleton("health_service", HealthService())
        self.container.register_singleton("metrics_service", MetricsService())

        # Register connectivity service with HTTP client
        http_client = self.container.resolve("http_client_service")
        self.container.register_singleton("connectivity_service", ConnectivityService(http_client))

        # Register scheduler and monitoring services
        self.container.register_singleton("scheduler_service", SchedulerService(config))
        self.container.register_singleton("monitoring_service", MonitoringService(config))
        self.container.register_singleton("storage_service", StorageService())

        # Register configuration and events
        self.container.register_singleton("config_manager", self.config_manager)
        self.container.register_singleton("event_bus", self.event_bus)
        self.container.register_singleton("lifecycle", self.lifecycle)

        # Register a factory for UnitOfWork if available
        try:
            if UnitOfWork is not None:
                self.container.register_factory("unit_of_work", lambda: UnitOfWork())
        except Exception:  # nosec B110 -- intentional broad except for resilience
            # Non-critical; continue without UoW service if registration fails
            pass

        # Publish service registration event
        self.event_bus.publish_simple(
            Events.APP_STARTING,
            data={
                "services_registered": [
                    "filesystem",
                    "http_client",
                    "connectivity",
                    "database",
                    "logging",
                    "health",
                    "metrics",
                    "scheduler",
                    "monitoring",
                    "storage",
                    "config",
                    "events",
                    "lifecycle",
                ]
            },
            source="core_application_factory",
        )

    def setup_configuration(self, config_dir: str = "/config") -> dict[str, Any]:
        """Setup application configuration with core architecture integration."""
        default_config = {
            "app": {"name": "researcharr", "version": "1.0.0", "debug": False},
            "logging": {
                "level": "INFO",
                "file": os.path.join(config_dir, "app.log"),
            },
            "database": {"path": "researcharr.db"},
            "general": {
                "PUID": os.getenv("PUID", "1000"),
                "PGID": os.getenv("PGID", "1000"),
                "Timezone": os.getenv("TIMEZONE", "America/New_York"),
                "LogLevel": os.getenv("LOGLEVEL", "INFO"),
            },
            "scheduling": {"cron_schedule": "0 0 * * *", "timezone": "UTC"},
            "user": {
                "username": "admin",
                "password": "password",
            },  # pragma: allowlist secret
            "backups": {
                "retain_count": 10,
                "retain_days": 30,
                "pre_restore": True,
                "pre_restore_keep_days": 1,
                "auto_backup_enabled": False,
                "auto_backup_cron": "0 2 * * *",
                "prune_cron": "0 3 * * *",
            },
            "tasks": {},
        }

        managed_sources = {"default_config", "tasks_config", "general_config"}
        try:
            sources = getattr(self.config_manager, "_sources", None)
            if isinstance(sources, list):
                self.config_manager._sources = [  # type: ignore[attr-defined]
                    src for src in sources if getattr(src, "name", None) not in managed_sources
                ]
        except Exception:  # nosec B110 -- best-effort cleanup only
            pass

        # Add configuration sources
        self.config_manager.add_source(
            "default_config",
            data=default_config,
            priority=100,
        )

        # Add configuration files
        self.config_manager.add_source(
            "tasks_config",
            path=os.path.join(config_dir, "tasks.yml"),
            required=False,
            priority=80,
        )

        self.config_manager.add_source(
            "general_config",
            path=os.path.join(config_dir, "general.yml"),
            required=False,
            priority=70,
        )

        try:
            success = self.config_manager.load_config(reload=True)
        except Exception:  # pragma: no cover - defensive guard
            LOGGER.exception("Configuration manager raised during load; using fallback defaults")
            success = False

        if success:
            return self._build_config_data_from_manager()

        LOGGER.warning(
            "Configuration manager failed to load sources for %s; falling back to defaults",
            config_dir,
        )
        try:
            errors = self.config_manager.validation_errors
            if errors:
                LOGGER.warning("Config validation errors: %s", errors)
        except Exception:  # pragma: no cover - best effort logging only
            pass

        fallback_config = self._build_fallback_config(default_config, config_dir)
        try:
            self.config_manager._config = fallback_config  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - best effort
            pass

        return self._build_config_data_from_manager()

    def _build_config_data_from_manager(self) -> dict[str, Any]:
        """Create a legacy-compatible config payload from the manager state."""
        return {
            "app": self.config_manager.get_section("app"),
            "logging": self.config_manager.get_section("logging"),
            "database": self.config_manager.get_section("database"),
            "general": self.config_manager.get_section("general"),
            "radarr": [],
            "sonarr": [],
            "scheduling": self.config_manager.get_section("scheduling"),
            "user": self.config_manager.get_section("user"),
            "backups": self.config_manager.get_section("backups"),
            "tasks": self.config_manager.get_section("tasks"),
        }

    def _build_fallback_config(self, defaults: dict[str, Any], config_dir: str) -> dict[str, Any]:
        """Construct a configuration snapshot without the config manager."""
        current_config: dict[str, Any] = {}
        try:
            existing = getattr(self.config_manager, "_config", {})
            if isinstance(existing, dict) and existing:
                current_config = deepcopy(existing)
        except Exception:  # pragma: no cover - defensive
            current_config = {}

        baseline = self._deep_merge_dicts(defaults, current_config)

        legacy_files = [
            os.path.join(config_dir, "config.yml"),
            os.path.join(config_dir, "general.yml"),
            os.path.join(config_dir, "tasks.yml"),
        ]

        for path in legacy_files:
            if not os.path.exists(path):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
                if isinstance(data, dict):
                    baseline = self._deep_merge_dicts(baseline, data)
            except Exception:
                LOGGER.warning("Failed to load fallback config file: %s", path, exc_info=True)

        return baseline

    @staticmethod
    def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge two dictionaries without mutating inputs."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = CoreApplicationFactory._deep_merge_dicts(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def setup_plugins(self, app: Flask, config_dir: str = "/config") -> Any:
        """Setup plugin registry and load plugin configurations."""
        try:
            # Import plugin registry with fallbacks
            registry = None
            try:
                import importlib as _importlib_mod

                try:
                    _reg_mod = _importlib_mod.import_module("researcharr.plugins.registry")
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    _reg_mod = _importlib_mod.import_module("plugins.registry")
                _PluginRegistryRuntime = _reg_mod.PluginRegistry
                registry = _PluginRegistryRuntime()
            except Exception:  # nosec B110 -- intentional broad except for resilience
                # Fallback to direct file loading
                pkg_dir = os.path.dirname(__file__)
                reg_path = os.path.join(pkg_dir, "..", "..", "plugins", "registry.py")
                if os.path.exists(reg_path):
                    spec = importlib.util.spec_from_file_location(
                        "researcharr.plugins.registry", reg_path
                    )
                    if spec and spec.loader:
                        plugin_mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(plugin_mod)
                        _PluginRegistryRuntime = plugin_mod.PluginRegistry
                        registry = _PluginRegistryRuntime()

            if registry:
                # Discover local plugins
                pkg_dir = os.path.dirname(__file__)
                plugins_dir = os.path.join(pkg_dir, "..", "..", "plugins")
                if os.path.exists(plugins_dir):
                    registry.discover_local(plugins_dir)

                # Register plugin registry as a service
                self.container.register_singleton("plugin_registry", registry)

                # Load plugin configurations
                plugins_config_dir = os.path.join(config_dir, "plugins")
                try:
                    os.makedirs(plugins_config_dir, exist_ok=True)
                    plugin_configs = {}

                    for name in registry.list_plugins():
                        cfg_file = os.path.join(plugins_config_dir, f"{name}.yml")
                        if os.path.exists(cfg_file):
                            try:
                                with open(cfg_file) as fh:
                                    data = yaml.safe_load(fh) or []
                                    plugin_configs[name] = data

                                    # Publish plugin loaded event
                                    self.event_bus.publish_simple(
                                        Events.PLUGIN_LOADED,
                                        data={"plugin": name, "instances": len(data)},
                                        source="core_application_factory",
                                    )
                            except Exception as e:  # nosec B110 -- intentional broad except for resilience
                                # Publish plugin error event
                                self.event_bus.publish_simple(
                                    Events.PLUGIN_ERROR,
                                    data={"plugin": name, "error": str(e)},
                                    source="core_application_factory",
                                )

                    # Update configuration with plugin configs
                    for name, config in plugin_configs.items():
                        self.config_manager.set(f"plugins.{name}", config, "plugin_loader")

                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass  # Best effort

                return registry

        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass  # Continue without plugins if loading fails

        return None

    def setup_user_authentication(self, config_dir: str = "/config") -> dict[str, Any]:
        """Setup user authentication with webui integration."""
        user_config = {
            "username": "admin",
            "password": "password",
        }  # pragma: allowlist secret

        try:
            # Try to load webui module for user config
            webui: ModuleType | None = None
            try:
                from researcharr import webui
            except Exception:  # nosec B110 -- intentional broad except for resilience
                # Fallback to direct import
                spec = importlib.util.spec_from_file_location(
                    "webui",
                    os.path.join(os.path.dirname(__file__), "..", "..", "webui.py"),
                )
                if spec and spec.loader:
                    webui = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(webui)
                else:
                    webui = None

            webui_module: ModuleType | None = webui

            if webui_module:
                try:
                    ucfg = webui_module.load_user_config()
                    if isinstance(ucfg, dict):
                        if "password_hash" in ucfg:
                            password_hash = ucfg.get("password_hash")
                            if password_hash:
                                user_config["password_hash"] = password_hash

                        # Handle API key migration
                        if "api_key_hash" in ucfg:
                            self.config_manager.set(
                                "general.api_key_hash", ucfg.get("api_key_hash")
                            )
                        elif "api_key" in ucfg:
                            # Migrate plaintext API key to hash
                            api_key_val = ucfg.get("api_key")  # pragma: allowlist secret
                            if api_key_val:
                                hashed = generate_password_hash(str(api_key_val))
                                webui_module.save_user_config(
                                    ucfg.get("username", user_config["username"]),
                                    ucfg.get("password_hash"),
                                    api_key_hash=hashed,
                                )
                                self.config_manager.set("general.api_key_hash", hashed)

                        # Publish user config loaded event
                        self.event_bus.publish_simple(
                            Events.CONFIG_LOADED,
                            data={
                                "type": "user_config",
                                "has_hash": "password_hash" in ucfg,
                            },
                            source="core_application_factory",
                        )

                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass  # Use defaults if loading fails

        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass  # Use defaults

        return user_config

    def setup_lifecycle_hooks(self) -> None:
        """Setup application lifecycle hooks."""

        def startup_database():
            """Initialize database on startup."""
            try:
                db_service = self.container.resolve("database_service")
                db_service.init_db()
            except Exception as e:  # nosec B110 -- intentional broad except for resilience
                self.event_bus.publish_simple(
                    Events.ERROR_OCCURRED,
                    data={"error": str(e), "component": "database_startup"},
                    source="lifecycle_hooks",
                )
                raise

        def startup_logging():
            """Setup logging on startup."""
            try:
                logging_service = self.container.resolve("logging_service")
                log_file = self.config_manager.get("logging.file", "/config/app.log")
                log_level = self.config_manager.get("logging.level", "INFO")

                # Convert string level to int
                import logging

                level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL,
                }
                level = level_map.get(log_level.upper(), logging.INFO)

                logging_service.setup_logger("researcharr", log_file, level)
            except Exception as e:  # nosec B110 -- intentional broad except for resilience
                self.event_bus.publish_simple(
                    Events.ERROR_OCCURRED,
                    data={"error": str(e), "component": "logging_startup"},
                    source="lifecycle_hooks",
                )
                # Don't raise - logging failure shouldn't stop startup

        def startup_scheduler():
            """Start the scheduler service."""
            try:
                scheduler_service = self.container.resolve("scheduler_service")
                if scheduler_service.start():
                    self.event_bus.publish_simple(
                        Events.APP_STARTED,
                        data={"component": "scheduler"},
                        source="lifecycle_hooks",
                    )
            except Exception as e:  # nosec B110 -- intentional broad except for resilience
                self.event_bus.publish_simple(
                    Events.ERROR_OCCURRED,
                    data={"error": str(e), "component": "scheduler_startup"},
                    source="lifecycle_hooks",
                )
                # Non-critical - app can run without scheduler

        def shutdown_scheduler():
            """Stop the scheduler service."""
            try:
                scheduler_service = self.container.resolve("scheduler_service")
                scheduler_service.stop()
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass  # Best effort

        def shutdown_cleanup():
            """Cleanup on shutdown."""
            try:
                self.event_bus.publish_simple(
                    Events.APP_STOPPING,
                    data={"reason": "normal_shutdown"},
                    source="lifecycle_hooks",
                )
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass  # Best effort

        # Register lifecycle hooks
        add_startup_hook("core_database", startup_database, priority=10, critical=True)
        add_startup_hook("core_logging", startup_logging, priority=20, critical=False)
        add_startup_hook("core_scheduler", startup_scheduler, priority=30, critical=False)
        add_shutdown_hook("core_scheduler", shutdown_scheduler, priority=10, critical=False)
        add_shutdown_hook("core_cleanup", shutdown_cleanup, priority=90, critical=False)

    def create_core_app(self, config_dir: str = "/config") -> Flask:
        """Create a minimal Flask app with core services only (no web UI)."""
        # Register services first
        self.register_core_services()

        # Setup configuration
        config_data = self.setup_configuration(config_dir)

        # Setup lifecycle hooks
        self.setup_lifecycle_hooks()

        # Create Flask app with type annotation to allow custom attributes
        app: Any = Flask("researcharr_core")

        # Basic Flask configuration
        app.secret_key = os.getenv("SECRET_KEY", "dev")
        app.config_data = config_data

        # Setup user authentication
        user_config = self.setup_user_authentication(config_dir)
        app.config_data["user"].update(user_config)

        # Setup plugins
        plugin_registry = self.setup_plugins(app, config_dir)
        if plugin_registry:
            app.plugin_registry = plugin_registry

        # Register core API
        try:
            from .api import bp as core_api_bp

            app.register_blueprint(core_api_bp, url_prefix="/api/v1")
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass  # Core API is optional

        # Setup metrics tracking
        try:
            metrics_service = self.container.resolve("metrics_service")
            app.metrics = metrics_service.get_metrics()

            @app.before_request
            def track_requests():
                metrics_service.increment_requests()

        except Exception:  # nosec B110 -- intentional broad except for resilience
            app.metrics = {"requests_total": 0, "errors_total": 0, "plugins": {}}

        return app


# Factory function for backwards compatibility
def create_core_app(config_dir: str = "/config") -> Flask:
    """Create a core application with clean architecture services.

    This provides a minimal Flask app with core services but no web UI.
    Use this for API-only deployments or as a base for web UI integration.
    """
    factory = CoreApplicationFactory()
    return factory.create_core_app(config_dir)


def integrate_with_web_app(app: Any, config_dir: str = "/config") -> Any:
    """Integrate core services with an existing Flask web app.

    This function adds core architecture services to an existing Flask app
    created by the main factory.py create_app() function.
    """
    factory = CoreApplicationFactory()

    # Register services
    factory.register_core_services()

    # Setup lifecycle hooks
    factory.setup_lifecycle_hooks()

    # Add core API if not already present
    try:
        from .api import bp as core_api_bp

        # Check if already registered
        if not any(bp.name == "api_v1" for bp in app.blueprints.values()):
            app.register_blueprint(core_api_bp, url_prefix="/api/v1")
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass

    # Enhance metrics with core services
    try:
        metrics_service = factory.container.resolve("metrics_service")
        if hasattr(app, "metrics") and isinstance(app.metrics, dict):
            # Merge existing metrics with core service
            existing_metrics = app.metrics.copy()
            metrics_service.metrics.update(existing_metrics)
            app.metrics = metrics_service.get_metrics()
    except Exception:  # nosec B110 -- intentional broad except for resilience
        pass

    return app
