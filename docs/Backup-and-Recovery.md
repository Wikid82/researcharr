# Backup and Recovery Procedures

This guide provides comprehensive backup and recovery procedures for ResearchArr operators. It covers backup strategies, recovery procedures, automated scheduling, and best practices.

## Overview

ResearchArr includes built-in backup and recovery capabilities:

- **Automated backups** - Scheduled backups via configuration
- **Manual backups** - CLI and API for on-demand backups
- **Safe restores** - Automatic rollback on failure
- **Retention policies** - Configurable backup pruning
- **Monitoring** - Backup health metrics and alerts
- **Validation** - Integrity checking before restore

## Backup Strategy

### What Gets Backed Up

Backups include:
- **Database** - `researcharr.db` (application data)
- **Configuration** - `config.yml` and related files
- **Metadata** - Backup timestamp, compression info

Backups do **not** include:
- Application code
- Docker images
- Logs (backed up separately)
- Temporary files

### Backup Types

**Full Backups**
- Complete database and configuration snapshot
- Compressed with configurable compression level
- Self-contained and portable

**Pre-Restore Snapshots**
- Automatic snapshot before restore operations
- Enables rollback if restore fails
- Temporary, cleaned up after successful restore

### Retention Policy

Configure retention in `config.yml`:

```yaml
backup:
  retention_count: 7        # Keep last 7 backups
  auto_backup_enabled: true # Enable automatic backups
  backup_schedule_cron: "0 2 * * *"  # Daily at 2 AM
```

Retention strategies:
- **Daily**: 7-14 days of backups
- **Weekly**: 4-8 weeks of backups
- **Monthly**: 6-12 months of backups

Use multiple strategies:
```bash
# Keep 7 daily backups
0 2 * * * researcharr-cli backup create && researcharr-cli backup prune --keep 7

# Keep 4 weekly backups (Sunday)
0 3 * * 0 researcharr-cli backup create && researcharr-cli backup prune --keep 4
```

## Creating Backups

### Automatic Backups

Enable in configuration:

```yaml
backup:
  auto_backup_enabled: true
  backup_schedule_cron: "0 2 * * *"  # Daily at 2 AM
  compression_level: 6
  retention_count: 7
```

The scheduler will:
1. Create backup at scheduled time
2. Validate backup integrity
3. Prune old backups per retention policy
4. Publish metrics and alerts

### Manual Backups

#### Via CLI

```bash
# Create backup with default compression
researcharr-cli backup create

# Create backup with maximum compression
researcharr-cli backup create --compression 9

# List backups
researcharr-cli backup list
```

#### Via API

```bash
# Create backup
curl -X POST http://localhost:2929/api/backups

# List backups
curl http://localhost:2929/api/backups

# Get backup info
curl http://localhost:2929/api/backups/backup_20250110_120000.tar.gz
```

### Pre-Upgrade Backups

Always create a backup before upgrading:

```bash
#!/bin/bash
set -e

# Create pre-upgrade backup
echo "Creating pre-upgrade backup..."
researcharr-cli backup create

# Verify backup
LATEST=$(researcharr-cli backup list --json | jq -r '.[0].filename')
researcharr-cli backup validate "$LATEST"

# Proceed with upgrade
echo "Backup verified. Proceeding with upgrade..."
```

## Restoring Backups

### Restore Process

The restore operation follows these steps:

1. **Pre-Restore Snapshot** - Create snapshot of current state
2. **Validation** - Verify backup integrity
3. **Schema Check** - Ensure backup is compatible
4. **Restore** - Apply backup to database and config
5. **Integrity Check** - Verify restored data
6. **Rollback** - Automatic rollback if checks fail

### Via CLI

```bash
# List available backups
researcharr-cli backup list

# Restore from specific backup
researcharr-cli backup restore backup_20250110_120000.tar.gz

# Force restore without confirmation
researcharr-cli backup restore backup_20250110_120000.tar.gz --force

# Restore without automatic rollback (not recommended)
researcharr-cli backup restore backup_20250110_120000.tar.gz --no-rollback
```

### Via API

```bash
# Restore from backup
curl -X POST http://localhost:2929/api/backups/backup_20250110_120000.tar.gz/restore
```

### Restore Results

The restore operation returns detailed results:

```json
{
  "success": true,
  "message": "Backup restored successfully",
  "backup_file": "backup_20250110_120000.tar.gz",
  "pre_restore_snapshot": "pre_restore_20250110_130000.tar.gz",
  "restored_at": "2025-01-10T13:00:00Z",
  "rollback_executed": false,
  "integrity_passed": true
}
```

If restore fails:

```json
{
  "success": false,
  "message": "Integrity check failed after restore, rolled back to snapshot",
  "backup_file": "backup_20250110_120000.tar.gz",
  "pre_restore_snapshot": "pre_restore_20250110_130000.tar.gz",
  "rollback_executed": true,
  "error": "Database integrity check failed"
}
```

## Monitoring and Alerts

### Backup Health Monitoring

The backup monitor tracks:
- **Last backup timestamp** - Time of most recent backup
- **Backup count** - Total number of backups
- **Failed backups** - Count of failed backup attempts
- **Stale backups** - Warning if backups are too old

### Metrics

View metrics at `/metrics` endpoint:

```
# HELP backup_count Total number of backups
# TYPE backup_count gauge
backup_count 7

# HELP backup_last_timestamp Timestamp of last successful backup
# TYPE backup_last_timestamp gauge
backup_last_timestamp 1736510400

# HELP backup_failed_count Number of failed backup attempts
# TYPE backup_failed_count counter
backup_failed_count 0

# HELP backup_stale Indicates if backups are stale (1) or current (0)
# TYPE backup_stale gauge
backup_stale 0
```

### Alerting

Configure alerting in monitoring system:

**Prometheus Alert Rules**:

```yaml
groups:
  - name: backup_alerts
    rules:
      - alert: BackupStale
        expr: backup_stale == 1
        for: 1h
        annotations:
          summary: "ResearchArr backups are stale"
          description: "No backup created in configured threshold"

      - alert: BackupFailed
        expr: increase(backup_failed_count[1h]) > 0
        annotations:
          summary: "ResearchArr backup failed"
          description: "Backup operation failed {{ $value }} times in last hour"

      - alert: NoRecentBackup
        expr: time() - backup_last_timestamp > 86400 * 2
        annotations:
          summary: "No ResearchArr backup in 2 days"
          description: "Last backup was {{ $value | humanizeDuration }} ago"
```

### Event Bus Integration

Backup events are published to the event bus:

- `BACKUP_CREATED` - Backup successfully created
- `BACKUP_FAILED` - Backup creation failed
- `BACKUP_RESTORED` - Backup successfully restored
- `BACKUP_RESTORE_FAILED` - Restore operation failed
- `BACKUP_PRUNED` - Old backups pruned
- `BACKUP_STALE` - Backups are stale
- `BACKUP_VALIDATION_FAILED` - Backup validation failed
- `PRE_RESTORE_SNAPSHOT_CREATED` - Pre-restore snapshot created
- `RESTORE_ROLLBACK_EXECUTED` - Restore rollback executed

Subscribe to events for custom alerting:

```python
from researcharr.core.events import get_event_bus

def on_backup_failed(event_data):
    # Send alert
    send_alert("Backup failed", event_data)

event_bus = get_event_bus()
event_bus.subscribe("BACKUP_FAILED", on_backup_failed)
```

## Validation and Integrity

### Validate Backups

Verify backup integrity without restoring:

```bash
# Validate specific backup
researcharr-cli backup validate backup_20250110_120000.tar.gz

# Validate all backups
researcharr-cli backup list --json | \
  jq -r '.[].filename' | \
  xargs -I {} researcharr-cli backup validate {}
```

### Integrity Checks

Backups are validated for:
- **Archive integrity** - Valid tar.gz format
- **Required files** - Database and config present
- **Metadata** - Backup metadata is valid
- **Schema version** - Compatible schema version

Before restore:
- Backup integrity validated
- Schema compatibility checked
- Pre-restore snapshot created

After restore:
- Database integrity verified
- Configuration validated
- Automatic rollback if checks fail

## Best Practices

### Backup Frequency

**Production Systems**:
- Daily automated backups
- Pre-upgrade manual backups
- Before major configuration changes

**Development Systems**:
- Weekly automated backups
- Before testing major changes

### Backup Location

**Local Backups**:
```yaml
backup:
  backup_dir: /config/backups
```

**Remote Backups** (recommended):
```bash
# Sync to remote storage after backup
0 3 * * * researcharr-cli backup create && \
  rsync -avz /config/backups/ backup-server:/backups/researcharr/
```

**Cloud Storage**:
```bash
# Upload to S3
0 3 * * * researcharr-cli backup create && \
  aws s3 sync /config/backups/ s3://my-bucket/researcharr-backups/
```

### Testing Restores

**Regular restore testing** is critical:

```bash
#!/bin/bash
# Monthly restore test

# Create test backup
TEST_BACKUP=$(researcharr-cli backup create | grep "Created backup" | awk '{print $3}')

# Validate backup
researcharr-cli backup validate "$TEST_BACKUP"

# In test environment, restore backup
researcharr-cli backup restore "$TEST_BACKUP" --force

# Verify application health
researcharr-cli health

# Log results
echo "Restore test successful: $TEST_BACKUP" | \
  mail -s "ResearchArr Restore Test" admin@example.com
```

### Retention Strategy

**3-2-1 Backup Rule**:
- **3** copies of data
- **2** different storage types
- **1** off-site copy

Example:
```bash
#!/bin/bash
# Daily backup with 3-2-1 strategy

# Create local backup
researcharr-cli backup create

# Copy to NAS (2nd storage)
rsync -avz /config/backups/ /mnt/nas/researcharr/

# Copy to cloud (off-site)
aws s3 sync /config/backups/ s3://my-bucket/researcharr/

# Prune old backups locally
researcharr-cli backup prune --keep 7

# Prune old backups on NAS
find /mnt/nas/researcharr/ -name "backup_*.tar.gz" -mtime +30 -delete

# Keep cloud backups for 90 days
aws s3 ls s3://my-bucket/researcharr/ | \
  awk '{print $4}' | \
  while read file; do
    age=$((($(date +%s) - $(date -d "$(echo $file | cut -d_ -f2 | cut -d. -f1)" +%s))/86400))
    if [ $age -gt 90 ]; then
      aws s3 rm "s3://my-bucket/researcharr/$file"
    fi
  done
```

### Compression Levels

Balance compression vs. speed:

- **Level 0** - No compression, fastest
- **Level 6** - Default, good balance
- **Level 9** - Maximum compression, slowest

Example:
```yaml
backup:
  compression_level: 6  # Balanced
```

For large databases:
```yaml
backup:
  compression_level: 3  # Faster backups
```

For archival:
```bash
# Maximum compression for long-term storage
researcharr-cli backup create --compression 9
```

### Documentation

Document your backup procedures:

- Backup schedule and retention
- Restore procedures
- Contact information
- Storage locations
- Testing schedule

Example runbook:
```markdown
# ResearchArr Backup Procedures

## Schedule
- Daily: 2 AM UTC (automated)
- Pre-upgrade: Manual
- Pre-change: Manual

## Retention
- Local: 7 days
- NAS: 30 days
- S3: 90 days

## Restore Procedure
1. Stop application
2. List backups: `researcharr-cli backup list`
3. Restore: `researcharr-cli backup restore <file>`
4. Verify: `researcharr-cli health`
5. Start application

## Contacts
- Primary: ops@example.com
- Secondary: admin@example.com

## Storage
- Local: /config/backups
- NAS: /mnt/nas/researcharr
- S3: s3://my-bucket/researcharr
```

## Troubleshooting

### Backup Creation Fails

**Check disk space**:
```bash
df -h /config/backups
```

**Check permissions**:
```bash
ls -la /config/backups
```

**Check logs**:
```bash
tail -f /config/logs/researcharr.log
```

### Restore Fails

**Validate backup first**:
```bash
researcharr-cli backup validate backup_20250110_120000.tar.gz
```

**Check schema compatibility**:
```bash
researcharr-cli backup info backup_20250110_120000.tar.gz | grep schema
```

**Force restore** (if validation passes):
```bash
researcharr-cli backup restore backup_20250110_120000.tar.gz --force
```

### Rollback Executed

If automatic rollback occurs:

1. Check logs for failure reason
2. Validate backup integrity
3. Check schema compatibility
4. Retry with validated backup

### Stale Backups Alert

If backups are stale:

1. Check if backup schedule is running
2. Verify scheduler service is active
3. Check for disk space issues
4. Review backup logs for errors

## See Also

- [CLI Usage Guide](CLI-Usage.md) - CLI command reference
- [Disaster Recovery Guide](Disaster-Recovery.md) - Disaster recovery procedures
- [Health and Metrics](Health-and-Metrics.md) - Monitoring and metrics
- [Deployment Guide](Deployment-and-Resources.md) - Deployment best practices
