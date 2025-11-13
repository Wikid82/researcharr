# CLI Usage Guide

ResearchArr provides a comprehensive command-line interface (CLI) for managing backups, checking system health, managing the database, executing jobs, and viewing configuration. This allows operators to manage the system without requiring access to the web UI.

## Installation

The CLI is automatically installed when you install ResearchArr:

```bash
pip install -e .
```

The `researcharr-cli` command will be available in your PATH.

## Command Overview

```
researcharr-cli <command> [options]
```

Available commands:
- `backup` - Backup and restore operations
- `health` - Application health checks
- `db` - Database management
- `run` - Execute scheduled jobs manually
- `config` - Configuration management

Use `researcharr-cli <command> --help` for detailed help on any command.

---

## Backup Commands

### Create Backup

Create a new backup of the application database and configuration:

```bash
researcharr-cli backup create
```

Options:
- `--compression <level>` - Compression level (0-9, default: 6)

Example:
```bash
researcharr-cli backup create --compression 9
```

### List Backups

List all available backups with details:

```bash
researcharr-cli backup list
```

Options:
- `--json` - Output in JSON format for scripting

Example output:
```
Available backups:
  backup_20250110_120000.tar.gz
    Created: 2025-01-10 12:00:00 UTC
    Size: 2.5 MB
    Compression: 6
    Database: researcharr.db (1.8 MB)
    Config files: 3
```

### Restore Backup

Restore from a backup file with automatic rollback on failure:

```bash
researcharr-cli backup restore backup_20250110_120000.tar.gz
```

Options:
- `--force` - Skip confirmation prompt
- `--no-rollback` - Disable automatic rollback on failure (not recommended)

The restore operation:
1. Creates a pre-restore snapshot
2. Validates the backup integrity
3. Checks schema compatibility
4. Restores database and configuration
5. Automatically rolls back if integrity checks fail

Example:
```bash
researcharr-cli backup restore backup_20250110_120000.tar.gz --force
```

### Prune Old Backups

Remove old backups based on retention policy:

```bash
researcharr-cli backup prune
```

Options:
- `--keep <count>` - Number of recent backups to keep (default: from config)
- `--dry-run` - Show what would be deleted without deleting

Example:
```bash
researcharr-cli backup prune --keep 7 --dry-run
```

### Validate Backup

Verify backup integrity without restoring:

```bash
researcharr-cli backup validate backup_20250110_120000.tar.gz
```

Options:
- `--json` - Output validation results in JSON format

### Backup Info

Display detailed information about a backup:

```bash
researcharr-cli backup info backup_20250110_120000.tar.gz
```

Options:
- `--json` - Output in JSON format

---

## Health Commands

Check application health status:

```bash
researcharr-cli health
```

Options:
- `--json` - Output in JSON format for monitoring systems

Example output:
```
Application Health Status:
  Overall Status: OK
  Database: OK
  Configuration: OK
  Last Backup: 2 hours ago
  Disk Space: 45% used
```

Use in monitoring scripts:
```bash
#!/bin/bash
if researcharr-cli health --json | jq -e '.status == "ok"' > /dev/null; then
    echo "System healthy"
    exit 0
else
    echo "System unhealthy"
    exit 1
fi
```

---

## Database Commands

### Initialize Database

Initialize or migrate the database schema:

```bash
researcharr-cli db init
```

This command:
- Creates database tables if they don't exist
- Runs pending migrations
- Validates schema integrity

Use this after installation or upgrades.

### Check Database

Verify database integrity and connectivity:

```bash
researcharr-cli db check
```

Options:
- `--json` - Output in JSON format

Example output:
```
Database Status:
  Connection: OK
  Schema Version: 1.2.0
  Integrity: OK
  Tables: 12
  Total Records: 1,234
```

---

## Run Commands

Execute scheduled jobs manually:

```bash
researcharr-cli run <job-name>
```

Available jobs:
- `sync` - Synchronize with external services
- `cleanup` - Clean up temporary files
- `backup` - Run scheduled backup
- `health-check` - Run health monitoring

Examples:
```bash
# Run sync job
researcharr-cli run sync

# Run backup job
researcharr-cli run backup

# Run cleanup
researcharr-cli run cleanup
```

---

## Configuration Commands

### Show Configuration

Display current configuration:

```bash
researcharr-cli config show
```

Options:
- `--json` - Output in JSON format
- `--section <name>` - Show specific section only

Examples:
```bash
# Show all configuration
researcharr-cli config show

# Show only backup configuration
researcharr-cli config show --section backup

# Export configuration as JSON
researcharr-cli config show --json > config.json
```

---

## Common Use Cases

### Daily Backup

Create a backup and prune old ones:

```bash
#!/bin/bash
researcharr-cli backup create && \
researcharr-cli backup prune --keep 7
```

### Health Monitoring

Check health and send alerts:

```bash
#!/bin/bash
HEALTH=$(researcharr-cli health --json)
STATUS=$(echo "$HEALTH" | jq -r '.status')

if [ "$STATUS" != "ok" ]; then
    echo "Alert: ResearchArr unhealthy" | mail -s "ResearchArr Alert" admin@example.com
fi
```

### Disaster Recovery

Restore from backup:

```bash
#!/bin/bash
# Stop the application
systemctl stop researcharr

# Restore from latest backup
LATEST=$(researcharr-cli backup list --json | jq -r '.[0].filename')
researcharr-cli backup restore "$LATEST" --force

# Start the application
systemctl start researcharr

# Verify health
researcharr-cli health
```

### Pre-Upgrade Backup

Create a backup before upgrading:

```bash
#!/bin/bash
# Create pre-upgrade backup
researcharr-cli backup create

# Upgrade
pip install --upgrade researcharr

# Migrate database
researcharr-cli db init

# Verify
researcharr-cli health
```

---

## Automation Examples

### Cron Job for Daily Backups

Add to crontab:

```cron
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/researcharr-cli backup create && /usr/local/bin/researcharr-cli backup prune --keep 7
```

### Systemd Timer for Backups

Create `/etc/systemd/system/researcharr-backup.service`:

```ini
[Unit]
Description=ResearchArr Backup
After=network.target

[Service]
Type=oneshot
User=researcharr
ExecStart=/usr/local/bin/researcharr-cli backup create
ExecStartPost=/usr/local/bin/researcharr-cli backup prune --keep 7
```

Create `/etc/systemd/system/researcharr-backup.timer`:

```ini
[Unit]
Description=ResearchArr Daily Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable researcharr-backup.timer
systemctl start researcharr-backup.timer
```

---

## Exit Codes

The CLI uses standard exit codes:

- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Operation failed (e.g., backup creation failed)
- `4` - Resource not found (e.g., backup file not found)

Use exit codes in scripts:

```bash
#!/bin/bash
if researcharr-cli backup create; then
    echo "Backup successful"
else
    echo "Backup failed with code $?"
    exit 1
fi
```

---

## JSON Output

Most commands support `--json` for machine-readable output. This is useful for:
- Monitoring systems (Prometheus, Nagios, etc.)
- Automation scripts
- CI/CD pipelines
- Custom dashboards

Example:
```bash
researcharr-cli backup list --json | jq '.[0]'
```

Output:
```json
{
  "filename": "backup_20250110_120000.tar.gz",
  "path": "/config/backups/backup_20250110_120000.tar.gz",
  "created": "2025-01-10T12:00:00Z",
  "size": 2621440,
  "compression": 6,
  "files": [
    {
      "name": "researcharr.db",
      "size": 1884160
    }
  ]
}
```

---

## Troubleshooting

### Command Not Found

If `researcharr-cli` is not found, ensure it's installed:

```bash
pip show researcharr
which researcharr-cli
```

### Permission Denied

Ensure the CLI has access to configuration and data directories:

```bash
ls -la /config
```

Run with appropriate user:

```bash
sudo -u researcharr researcharr-cli backup create
```

### Backup Fails

Check disk space:

```bash
df -h /config/backups
```

Check logs:

```bash
tail -f /config/logs/researcharr.log
```

### Database Locked

If database is locked, ensure no other instances are running:

```bash
ps aux | grep researcharr
systemctl status researcharr
```

---

## See Also

- [Backup and Recovery Guide](Backup-and-Recovery.md) - Comprehensive backup strategies
- [Disaster Recovery Guide](Disaster-Recovery.md) - Disaster recovery procedures
- [Deployment Guide](Deployment-and-Resources.md) - Deployment best practices
- [Health and Metrics](Health-and-Metrics.md) - Monitoring and metrics
