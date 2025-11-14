from researcharr.core.config_validator import (
    ConfigValidator,
    apply_config_defaults,
    get_validator,
    validate_config,
)

"""Core Application Architecture.

This module provides the foundational architecture components for the
researcharr application, implementing clean architecture principles with
dependency injection, event-driven communication, and lifecycle management.
"""

from .api import bp as core_api_blueprint
from .application import (
    CoreApplicationFactory,
    create_core_app,
    integrate_with_web_app,
)
from .config import (
    ConfigSource,
    ConfigurationManager,
    get_config,
    get_config_manager,
    load_config,
    set_config,
)
from .container import ServiceContainer, get_container
from .events import (
    Event,
    EventBus,
    Events,
    get_event_bus,
    publish_simple,
    subscribe,
)
from .lifecycle import (
    ApplicationLifecycle,
    ApplicationState,
    add_shutdown_hook,
    add_startup_hook,
    get_lifecycle,
)
from .services import (
    ConnectivityService,
    DatabaseService,
    HealthService,
    LoggingService,
    MetricsService,
    MonitoringService,
    SchedulerService,
    StorageService,
    check_radarr_connection,
    check_sonarr_connection,
    create_metrics_app,
    has_valid_url_and_key,
    init_db,
    serve,
    setup_logger,
)
from .services import load_config as load_config_legacy

# Job Queue System
from .jobs import (
    JobDefinition,
    JobPriority,
    JobProgress,
    JobQueue,
    JobResult,
    JobService,
    JobStatus,
    WorkerInfo,
    WorkerPool,
    WorkerStatus,
)

__all__ = [
    # Service Container
    "ServiceContainer",
    "get_container",
    # Event System
    "EventBus",
    "Event",
    "Events",
    "get_event_bus",
    "publish_simple",
    "subscribe",
    # Job Queue System
    "JobService",
    "JobQueue",
    "JobDefinition",
    "JobResult",
    "JobProgress",
    "JobStatus",
    "JobPriority",
    "WorkerPool",
    "WorkerInfo",
    "WorkerStatus",
    # Lifecycle Management
    "ApplicationLifecycle",
    "apply_config_defaults",
    "ConfigValidator",
    "ApplicationState",
    "get_lifecycle",
    "add_startup_hook",
    "add_shutdown_hook",
    # Configuration Management
    "ConfigurationManager",
    "ConfigSource",
    "get_config_manager",
    "get_config",
    "set_config",
    "load_config",
    # Core Services
    "DatabaseService",
    "LoggingService",
    "ConnectivityService",
    "HealthService",
    "MetricsService",
    "SchedulerService",
    "MonitoringService",
    "StorageService",
    "create_metrics_app",
    "serve",
    # Backwards Compatibility Functions
    "init_db",
    "setup_logger",
    "load_config_legacy",
    "has_valid_url_and_key",
    "check_radarr_connection",
    "check_sonarr_connection",
    # API
    "core_api_blueprint",
    # Application Factory
    "CoreApplicationFactory",
    "get_validator",
    "validate_config",
    "create_core_app",
    "integrate_with_web_app",
]
