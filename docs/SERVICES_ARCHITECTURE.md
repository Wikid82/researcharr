# Services Architecture

This document describes the core services architecture in Researcharr, including the integrated scheduler, monitoring, storage, and configuration validation services.

## Overview

Researcharr uses a service-oriented architecture with dependency injection. Core services are registered as singletons in a `ServiceContainer` and can be accessed throughout the application.

## Core Services

### 1. DatabaseService

Manages database connections and provides transaction support.

**Key Methods:**
- `initialize()`: Set up database connection
- `get_session()`: Get SQLAlchemy session
- `execute_query(query)`: Execute raw SQL

### 2. LoggingService

Provides centralized logging with configurable levels and formatters.

**Key Methods:**
- `get_logger(name)`: Get a named logger
- `set_level(level)`: Change logging level
- `add_handler(handler)`: Add custom log handler

### 3. ConnectivityService

Monitors network connectivity and handles connection state.

**Key Methods:**
- `is_connected()`: Check if connected to network
- `wait_for_connection()`: Block until connected
- `add_listener(callback)`: Register connectivity callback

### 4. HealthService

Aggregates health status from all health monitors.

**Key Methods:**
- `check_health()`: Get overall health status
- `register_monitor(monitor)`: Add a health monitor
- `get_metrics()`: Get health metrics

### 5. MetricsService

Collects and exposes application metrics.

**Key Methods:**
- `record_metric(name, value)`: Record a metric
- `get_metrics()`: Get all metrics
- `expose()`: Export metrics (Prometheus format)

### 6. SchedulerService

Manages scheduled tasks using APScheduler.

**Key Methods:**
- `initialize()`: Set up scheduler
- `start()`: Start scheduler
- `stop()`: Stop scheduler
- `add_job(func, trigger, **kwargs)`: Schedule a job
- `get_schedule_info()`: Get info about scheduled jobs
- `is_running()`: Check if scheduler is running

**Example:**
```python
from researcharr.core import SchedulerService
from apscheduler.triggers.cron import CronTrigger

scheduler = SchedulerService(config)
scheduler.initialize()
scheduler.start()

# Schedule a daily job
scheduler.add_job(
    my_function,
    CronTrigger(hour=2, minute=0),
    id="daily_job",
    name="Daily Task"
)
```

### 7. MonitoringService

Orchestrates health monitors (backup and database monitoring).

**Key Methods:**
- `initialize()`: Set up monitors
- `check_all_health()`: Run all health checks
- `get_all_metrics()`: Get metrics from all monitors
- `get_backup_health()`: Get backup health specifically
- `get_database_health()`: Get database health specifically

**Example:**
```python
from researcharr.core import MonitoringService

monitoring = MonitoringService(config)
monitoring.initialize()

# Check all health
health = monitoring.check_all_health()
print(f"Status: {health['status']}")
print(f"Alerts: {len(health['alerts'])}")

# Get specific metrics
db_metrics = monitoring.get_database_health()
```

### 8. StorageService

Provides simplified access to repository layer.

**Key Methods:**
- `initialize()`: Set up storage
- `create_unit_of_work()`: Create UnitOfWork context manager
- `get_app(app_id)`: Get managed app by ID
- `get_all_apps()`: Get all managed apps
- `get_enabled_apps()`: Get enabled apps
- `get_tracked_item(item_id)`: Get tracked item
- `get_processing_logs(limit)`: Get processing logs
- `get_setting(key, default)`: Get setting value
- `set_setting(key, value)`: Set setting value

**Example:**
```python
from researcharr.core import StorageService

storage = StorageService()
storage.initialize()

# Get all enabled apps
apps = storage.get_enabled_apps()
for app in apps:
    print(f"App: {app.name}")

# Get a setting with default
api_key = storage.get_setting("api_key", "")

# Update a setting
storage.set_setting("last_sync", "2024-01-15")
```

## Configuration Validation

The `ConfigValidator` service validates configuration against JSON-like schemas and applies defaults.

**Supported Sections:**
- `scheduling`: Scheduler configuration
- `backups`: Backup monitoring configuration
- `database`: Database monitoring configuration
- `storage`: Storage settings

**Example:**
```python
from researcharr.core import validate_config, apply_config_defaults

config = {
    "scheduling": {"timezone": "America/New_York"},
    "backups": {"retain_count": 10}
}

# Validate configuration
is_valid, errors = validate_config(config)
if not is_valid:
    print(f"Configuration errors: {errors}")

# Apply defaults for missing values
config = apply_config_defaults(config)
```

**Getting Schema Documentation:**
```python
from researcharr.core import get_validator

validator = get_validator()

# Get all schema docs
docs = validator.get_schema_docs()
print(docs)

# Get specific schema docs
scheduling_docs = validator.get_schema_docs("scheduling")
print(scheduling_docs)
```

## Service Container

All services are registered in a `ServiceContainer` which provides dependency injection.

**Usage:**
```python
from researcharr.core import get_container

container = get_container()

# Resolve a service
scheduler = container.resolve("scheduler_service")
monitoring = container.resolve("monitoring_service")
storage = container.resolve("storage_service")
```

## Event Bus

Services communicate via an event bus using a publish-subscribe pattern.

**Event Types:**
- `APP_STARTING`: Application is starting
- `APP_STARTED`: Application has started
- `APP_STOPPING`: Application is stopping
- `APP_STOPPED`: Application has stopped
- Database health events (7 types)
- Backup events

**Example:**
```python
from researcharr.core import get_container
from researcharr.events.events import publish_simple

def my_handler(event):
    print(f"Received event: {event.event_type}")

# Subscribe to events
container = get_container()
event_bus = container.resolve("event_bus")
event_bus.subscribe("BACKUP_STARTED", my_handler)

# Publish an event
publish_simple("CUSTOM_EVENT", {"data": "value"})
```

## Application Lifecycle

The application follows a defined lifecycle:

1. **Initialization**: Services are registered in the container
2. **Starting**: `APP_STARTING` event is published
3. **Startup**: Scheduler is started
4. **Running**: Application serves requests
5. **Stopping**: `APP_STOPPING` event is published
6. **Shutdown**: Scheduler is stopped
7. **Stopped**: `APP_STOPPED` event is published

**Lifecycle Hooks:**
```python
from researcharr.core import ApplicationLifecycle

lifecycle = ApplicationLifecycle()

# Register startup hook
def on_startup():
    print("Application starting")

lifecycle.register_startup_hook(on_startup)

# Register shutdown hook
def on_shutdown():
    print("Application stopping")

lifecycle.register_shutdown_hook(on_shutdown)
```

## Health Monitoring

### Backup Health Monitor

Monitors backup status and alerts on issues.

**Checks:**
- Backup age (too old?)
- Backup count (too few?)
- Backup size (too small/large?)
- Backup integrity

**Configuration:**
```yaml
backups:
  enabled: true
  retain_count: 5
  max_age_days: 30
  check_interval: 3600
```

### Database Health Monitor

Monitors database health and performance.

**Checks:**
- Connection status
- Database integrity (PRAGMA integrity_check)
- Database size and fragmentation
- WAL mode status
- Journal mode

**Configuration:**
```yaml
database:
  monitoring:
    enabled: true
    health_check_interval: 300
    integrity_check_interval: 86400
    size_alert_threshold_mb: 1000
    fragmentation_threshold: 0.3
```

## Scheduled Tasks

### Backup Scheduler

Schedules backup operations.

**Jobs:**
- Create backup (configurable schedule)
- Cleanup old backups (daily)

### Database Scheduler

Schedules database maintenance.

**Jobs:**
- Health checks (every 5 minutes)
- Integrity checks (daily)
- Statistics update (hourly)

## Best Practices

1. **Always initialize services**: Call `initialize()` before using a service
2. **Use dependency injection**: Resolve services from container, don't instantiate directly
3. **Handle errors gracefully**: Check return values from `initialize()`
4. **Validate configuration**: Use `validate_config()` before passing to services
5. **Use lifecycle hooks**: Register cleanup in shutdown hooks
6. **Monitor health**: Regularly check `MonitoringService.check_all_health()`
7. **Use StorageService**: Access repositories through StorageService, not UnitOfWork directly

## Integration Example

Complete example showing service integration:

```python
from researcharr.core import (
    CoreApplicationFactory,
    get_container,
    validate_config,
    apply_config_defaults
)

# Load and validate configuration
config = load_config()  # Your config loading logic
is_valid, errors = validate_config(config)
if not is_valid:
    raise ValueError(f"Invalid config: {errors}")

config = apply_config_defaults(config)

# Create application
factory = CoreApplicationFactory()
factory.register_core_services()
app = factory.create_app()

# Get services
container = get_container()
scheduler = container.resolve("scheduler_service")
monitoring = container.resolve("monitoring_service")
storage = container.resolve("storage_service")

# Initialize services
scheduler.initialize()
monitoring.initialize()
storage.initialize()

# Start scheduler
scheduler.start()

# Check health
health = monitoring.check_all_health()
print(f"Application health: {health['status']}")

# Use storage
apps = storage.get_enabled_apps()
print(f"Managing {len(apps)} apps")

# Application runs...

# Cleanup on shutdown
scheduler.stop()
```

## Testing

When testing code that uses services, use mocks:

```python
from unittest.mock import Mock, patch

def test_my_function():
    with patch("researcharr.core.get_container") as mock_container:
        mock_storage = Mock()
        mock_storage.get_enabled_apps.return_value = []
        mock_container.return_value.resolve.return_value = mock_storage

        # Your test code here
        result = my_function()
        assert result is not None
```

## Troubleshooting

**Scheduler not starting:**
- Check `scheduler.is_running()` returns `True`
- Verify `initialize()` was called and returned `True`
- Check logs for APScheduler errors

**Health checks failing:**
- Check database path is correct
- Verify database file permissions
- Check disk space

**Monitoring not working:**
- Verify `monitoring.initialize()` returns `True`
- Check configuration is valid
- Ensure monitors are enabled in config

**Storage errors:**
- Check database connection
- Verify migrations are up to date
- Check file permissions on database

## See Also

- [Configuration Schema Reference](CONFIGURATION.md)
- [Health Monitoring Guide](MONITORING.md)
- [Scheduler Integration](SCHEDULER.md)
- [API Documentation](API.md)
