# Configuration Reference

This document describes all configuration options for Researcharr services.

## Configuration Structure

Configuration can be loaded from YAML, JSON, or environment variables. The configuration validator ensures all values are within acceptable ranges.

## Scheduling Configuration

Controls the APScheduler-based task scheduler.

### `scheduling`

**scheduling.timezone** (string)
- Description: Timezone for scheduled tasks
- Default: `"UTC"`
- Examples: `"America/New_York"`, `"Europe/London"`, `"Asia/Tokyo"`

**scheduling.max_instances** (integer)
- Description: Maximum concurrent job instances
- Default: `3`
- Minimum: `1`
- Maximum: `10`
- Note: Prevents jobs from piling up if execution takes longer than interval

**scheduling.coalesce** (boolean)
- Description: Coalesce missed runs into single execution
- Default: `true`
- Note: If true, multiple missed runs execute as one; if false, all missed runs execute

### Example

```yaml
scheduling:
  timezone: "America/New_York"
  max_instances: 5
  coalesce: true
```

## Backup Configuration

Controls backup creation, retention, and monitoring.

### `backups`

**backups.enabled** (boolean)
- Description: Enable backup monitoring
- Default: `true`

**backups.retain_count** (integer)
- Description: Number of backups to retain
- Default: `5`
- Minimum: `1`
- Maximum: `100`
- Note: Older backups are automatically deleted

**backups.max_age_days** (integer)
- Description: Maximum age of backups in days
- Default: `30`
- Minimum: `1`
- Maximum: `365`
- Note: Backups older than this trigger warnings

**backups.check_interval** (integer)
- Description: Backup check interval in seconds
- Default: `3600` (1 hour)
- Minimum: `60` (1 minute)
- Maximum: `86400` (1 day)

### Example

```yaml
backups:
  enabled: true
  retain_count: 10
  max_age_days: 7
  check_interval: 3600
```

## Database Configuration

Controls database monitoring and health checks.

### `database`

**database.path** (string)
- Description: Database file path
- Example: `"/config/researcharr.db"`

**database.monitoring.enabled** (boolean)
- Description: Enable database monitoring
- Default: `true`

**database.monitoring.health_check_interval** (integer)
- Description: Health check interval in seconds
- Default: `300` (5 minutes)
- Minimum: `60` (1 minute)
- Maximum: `3600` (1 hour)
- Note: Basic health checks run at this interval

**database.monitoring.integrity_check_interval** (integer)
- Description: Full integrity check interval in seconds
- Default: `86400` (1 day)
- Minimum: `3600` (1 hour)
- Maximum: `604800` (1 week)
- Note: Integrity checks are expensive, run infrequently

**database.monitoring.size_alert_threshold_mb** (integer)
- Description: Database size alert threshold in MB
- Default: `1000` (1 GB)
- Minimum: `1`
- Maximum: `100000` (100 GB)
- Note: Alert when database exceeds this size

**database.monitoring.fragmentation_threshold** (number)
- Description: Fragmentation alert threshold (0-1)
- Default: `0.3` (30%)
- Minimum: `0.0`
- Maximum: `1.0`
- Note: Alert when fragmentation exceeds this percentage

### Example

```yaml
database:
  path: "/config/researcharr.db"
  monitoring:
    enabled: true
    health_check_interval: 300
    integrity_check_interval: 86400
    size_alert_threshold_mb: 1000
    fragmentation_threshold: 0.3
```

## Storage Configuration

Controls storage behavior and database settings.

### `storage`

**storage.backup_path** (string)
- Description: Path to backup directory
- Example: `"/config/backups"`

**storage.auto_vacuum** (boolean)
- Description: Enable automatic database vacuuming
- Default: `true`
- Note: Automatically reclaims space from deleted data

**storage.wal_mode** (boolean)
- Description: Enable Write-Ahead Logging mode
- Default: `true`
- Note: Improves concurrency and crash recovery

### Example

```yaml
storage:
  backup_path: "/config/backups"
  auto_vacuum: true
  wal_mode: true
```

## Complete Configuration Example

```yaml
# Scheduler configuration
scheduling:
  timezone: "America/New_York"
  max_instances: 5
  coalesce: true

# Backup configuration
backups:
  enabled: true
  retain_count: 10
  max_age_days: 7
  check_interval: 3600

# Database configuration
database:
  path: "/config/researcharr.db"
  monitoring:
    enabled: true
    health_check_interval: 300
    integrity_check_interval: 86400
    size_alert_threshold_mb: 1000
    fragmentation_threshold: 0.3

# Storage configuration
storage:
  backup_path: "/config/backups"
  auto_vacuum: true
  wal_mode: true
```

## Validation

Use the configuration validator to check configuration:

```python
from researcharr.core import validate_config, apply_config_defaults

# Load your config
config = load_config_from_file("config.yml")

# Validate
is_valid, errors = validate_config(config)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
    sys.exit(1)

# Apply defaults for missing values
config = apply_config_defaults(config)
```

## Environment Variables

Configuration can be overridden with environment variables:

```bash
# Scheduler
export RESEARCHARR_SCHEDULING_TIMEZONE="America/New_York"
export RESEARCHARR_SCHEDULING_MAX_INSTANCES=5

# Backups
export RESEARCHARR_BACKUPS_ENABLED=true
export RESEARCHARR_BACKUPS_RETAIN_COUNT=10

# Database
export RESEARCHARR_DATABASE_PATH="/config/researcharr.db"
export RESEARCHARR_DATABASE_MONITORING_ENABLED=true
```

## Configuration Precedence

Configuration sources are merged in this order (later overrides earlier):

1. Default values (from schema)
2. Configuration file (config.yml)
3. Environment variables

## Dynamic Configuration

Some configuration can be changed at runtime:

```python
from researcharr.core import get_container

container = get_container()
scheduler = container.resolve("scheduler_service")

# Configuration passed during initialization is static
# To change schedule, remove and re-add jobs:
scheduler.remove_job("my_job")
scheduler.add_job(my_func, new_trigger, id="my_job")
```

## Schema Documentation

Get documentation for all schemas:

```python
from researcharr.core import get_validator

validator = get_validator()
print(validator.get_schema_docs())
```

Get documentation for specific schema:

```python
validator = get_validator()
print(validator.get_schema_docs("scheduling"))
print(validator.get_schema_docs("backups"))
print(validator.get_schema_docs("database"))
print(validator.get_schema_docs("storage"))
```

## Troubleshooting

**"Unknown schema" error:**
- Check spelling of configuration section
- Ensure you're using supported sections: `scheduling`, `backups`, `database`, `storage`

**"Expected type" error:**
- Check value types match schema (string, integer, boolean)
- Use quotes for strings in YAML
- Don't quote booleans or numbers

**"Less than minimum" / "Greater than maximum" error:**
- Check value is within allowed range
- See min/max values in schema above

**"Invalid config" at startup:**
- Run config validation separately to see detailed errors
- Check for typos in configuration keys
- Ensure all required fields are present

## Best Practices

1. **Use defaults**: Only specify values you want to change from defaults
2. **Validate early**: Validate configuration at startup before initializing services
3. **Use version control**: Keep configuration in version control
4. **Document changes**: Comment why non-default values were chosen
5. **Test changes**: Test configuration changes in development first
6. **Monitor thresholds**: Adjust alert thresholds based on your environment
7. **Start conservative**: Use stricter thresholds initially, relax if needed

## See Also

- [Services Architecture](SERVICES_ARCHITECTURE.md)
- [Health Monitoring Guide](MONITORING.md)
- [Backup and Recovery](BACKUP_RECOVERY.md)
