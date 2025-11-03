# Core Application Architecture

This document describes the core application architecture implemented in the `researcharr.core` module as part of Issue #105.

## Overview

The core architecture implements clean architecture principles with four main components:

1. **Service Container** - Dependency injection and service management
2. **Event Bus** - Decoupled publish-subscribe messaging
3. **Application Lifecycle** - Startup/shutdown coordination with hooks
4. **Configuration Manager** - Centralized configuration with validation and change notification

## Components

### Service Container (`container.py`)

Provides dependency injection with multiple registration patterns:

- **Singleton**: Single instance shared across application
- **Factory**: New instance created on each request
- **Class**: Register class for later instantiation
- **Interface**: Register interface implementations

```python
from researcharr.core import get_container

container = get_container()

# Register services
container.register_singleton('database', database_instance)
container.register_factory('http_client', lambda: HttpClient())
container.register_class('processor', MediaProcessor)

# Resolve services
db = container.resolve('database')
processor = container.resolve('processor')
```

**Features:**
- Thread-safe operations
- Circular dependency detection
- Interface-based registration
- Global container instance

### Event Bus (`events.py`)

Implements publish-subscribe pattern for loose coupling:

```python
from researcharr.core import get_event_bus, Events, subscribe, publish_simple

# Subscribe to events
def handle_media_discovered(event):
    print(f"New media: {event.data}")

subscribe(Events.MEDIA_DISCOVERED, handle_media_discovered)

# Publish events
publish_simple(Events.MEDIA_DISCOVERED, {'title': 'Movie.mkv'})
```

**Features:**
- Thread-safe event handling
- Wildcard subscriptions (all events)
- Event history tracking
- Predefined event constants
- Error isolation (handler exceptions don't affect other handlers)

### Application Lifecycle (`lifecycle.py`)

Manages application startup and shutdown with prioritized hooks:

```python
from researcharr.core import add_startup_hook, add_shutdown_hook, get_lifecycle

# Add lifecycle hooks
add_startup_hook('database', init_database, priority=10, critical=True)
add_shutdown_hook('database', close_database, priority=90)

# Start application
lifecycle = get_lifecycle()
if lifecycle.startup():
    print("Application started successfully")
```

**Features:**
- Priority-based hook ordering
- Critical vs non-critical hooks
- Signal handling (SIGTERM, SIGINT)
- State management and tracking
- Context manager support
- Automatic cleanup on exit

### Configuration Manager (`config.py`)

Centralized configuration with validation and change notification:

```python
from researcharr.core import get_config_manager, get_config, load_config

# Add configuration sources
config_mgr = get_config_manager()
config_mgr.add_source('defaults', data={'app': {'name': 'researcharr'}})
config_mgr.add_source('user_config', path='config.yml', required=True)

# Load configuration
if load_config():
    app_name = get_config('app.name')
    print(f"Application: {app_name}")
```

**Features:**
- Multiple configuration sources with priority
- YAML and JSON file support
- Dot notation key access (`app.database.host`)
- Configuration validation
- Change notification and callbacks
- Runtime configuration updates
- File watching (planned)

## Integration Patterns

### Dependency Injection

Services are registered during application startup and resolved as needed:

```python
# Register core services
container.register_singleton('config', config_manager)
container.register_singleton('event_bus', event_bus)
container.register_class('media_processor', MediaProcessor)

# Services can depend on other services
class MediaProcessor:
    def __init__(self):
        self.config = get_container().resolve('config')
        self.event_bus = get_container().resolve('event_bus')
```

### Event-Driven Architecture

Components communicate through events rather than direct coupling:

```python
# Media scanner publishes discovery events
def scan_media():
    for file in media_files:
        publish_simple(Events.MEDIA_DISCOVERED, {'path': file})

# Multiple processors can handle the same event
subscribe(Events.MEDIA_DISCOVERED, metadata_processor)
subscribe(Events.MEDIA_DISCOVERED, thumbnail_generator)
subscribe(Events.MEDIA_DISCOVERED, indexer)
```

### Lifecycle Integration

All components participate in application lifecycle:

```python
def init_media_scanner():
    scanner = get_container().resolve('media_scanner')
    scanner.start()

def cleanup_media_scanner():
    scanner = get_container().resolve('media_scanner')
    scanner.stop()

add_startup_hook('media_scanner', init_media_scanner, priority=50)
add_shutdown_hook('media_scanner', cleanup_media_scanner, priority=50)
```

## Design Principles

### Clean Architecture

- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Components are open for extension, closed for modification
- **Interface Segregation**: Small, focused interfaces rather than large ones

### Event-Driven Design

- **Loose Coupling**: Components communicate through events, not direct references
- **Extensibility**: New functionality can be added by subscribing to existing events
- **Resilience**: Event handler failures don't affect other handlers or publishers

### Configuration Management

- **Single Source of Truth**: All configuration accessed through one manager
- **Environment Flexibility**: Multiple sources allow dev/staging/prod differences
- **Change Notification**: Components can react to configuration changes at runtime

## Thread Safety

All core components are thread-safe:

- **Service Container**: Uses `threading.RLock()` for registration/resolution
- **Event Bus**: Thread-safe event publishing and subscription management
- **Application Lifecycle**: Synchronized state transitions and hook execution
- **Configuration Manager**: Thread-safe configuration loading and updates

## Error Handling

Robust error handling throughout:

- **Service Container**: Circular dependency detection, missing service errors
- **Event Bus**: Handler exception isolation, optional error event publishing
- **Application Lifecycle**: Critical vs non-critical hook failure handling
- **Configuration Manager**: Validation errors, missing file handling

## Usage in Existing Codebase

The core architecture integrates with the existing `factory.py` patterns:

1. **Factory Function**: `create_app()` can use lifecycle hooks for initialization
2. **Plugin System**: Plugins can register services and subscribe to events
3. **Configuration**: Extends existing YAML configuration with validation
4. **Web UI**: Event system can notify UI of background processing updates

This provides a solid foundation for the Core Processing Engine implementation while maintaining compatibility with existing code patterns.
