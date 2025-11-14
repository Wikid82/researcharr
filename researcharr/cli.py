#!/usr/bin/env python3
# basedpyright: reportArgumentType=false
"""Command-line interface for ResearchArr backup and recovery operations.

This CLI provides operators with scriptable access to backup, restore, and
maintenance operations without requiring the web UI. Designed for automation,
disaster recovery scenarios, and operational procedures.

Usage:
    python -m researcharr.cli backup create [--config-dir DIR]
    python -m researcharr.cli backup list [--config-dir DIR] [--pattern PATTERN]
    python -m researcharr.cli backup restore BACKUP_NAME [--config-dir DIR] [--no-snapshot]
    python -m researcharr.cli backup prune [--config-dir DIR]
    python -m researcharr.cli backup validate BACKUP_NAME [--config-dir DIR]
    python -m researcharr.cli backup info BACKUP_NAME [--config-dir DIR]

Docker Usage:
    docker exec researcharr python -m researcharr.cli backup create
    docker exec researcharr python -m researcharr.cli backup list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

from researcharr import run as _run_module
from researcharr.backups import (
    create_backup_file,
    get_backup_info,
    get_backup_size,
    list_backups,
    prune_backups,
    restore_backup,
    validate_backup_file,
)
from researcharr.compat import UTC
from researcharr.core.services import DatabaseService, MonitoringService
from researcharr.monitoring import get_database_health_monitor
from researcharr.storage.recovery import (
    check_db_integrity,
    get_alembic_head_revision,
    read_backup_meta,
    snapshot_sqlite,
    suggest_image_tag_from_meta,
)


def get_config_dir() -> Path:
    """Get the configuration directory path from environment or default."""
    return Path(os.environ.get("CONFIG_DIR", "/config"))


def get_backups_dir(config_dir: Path | None = None) -> Path:
    """Get the backups directory path."""
    if config_dir is None:
        config_dir = get_config_dir()
    return config_dir / "backups"


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} TB"


def format_timestamp(ts_str: str | None) -> str:
    """Format ISO timestamp to readable string."""
    if not ts_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:  # nosec B110
        return ts_str


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new backup."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)

    print(f"Creating backup from: {config_dir}")
    print(f"Backup destination: {backups_dir}")

    try:
        backup_path = create_backup_file(config_dir, backups_dir, prefix=args.prefix)
        if backup_path is None:
            print("ERROR: Backup creation failed", file=sys.stderr)
            return 1

        size = get_backup_size(backup_path)
        print(f"✓ Backup created: {Path(backup_path).name}")
        print(f"  Size: {format_size(size)}")
        print(f"  Path: {backup_path}")
        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List available backups."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)

    try:
        backups = list_backups(backups_dir, pattern=args.pattern)

        if not backups:
            print("No backups found")
            return 0

        if args.json:
            print(json.dumps(backups, indent=2))
            return 0

        print(f"Found {len(backups)} backup(s) in {backups_dir}:\n")
        for backup in backups:
            name = backup.get("name", "unknown")
            size = backup.get("size", 0)
            timestamp = backup.get("timestamp", "")
            files = backup.get("files", 0)

            print(f"  {name}")
            print(f"    Created: {format_timestamp(timestamp)}")
            print(f"    Size:    {format_size(size)}")
            print(f"    Files:   {files}")
            print()

        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_restore(args: argparse.Namespace) -> int:
    """Restore from a backup."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)
    backup_path = backups_dir / args.backup_name

    if not backup_path.exists():
        print(f"ERROR: Backup not found: {backup_path}", file=sys.stderr)
        return 1

    print(f"Restoring from: {backup_path.name}")
    print(f"Destination: {config_dir}")

    # Validate backup before restore
    if not validate_backup_file(backup_path):
        print("ERROR: Backup validation failed", file=sys.stderr)
        return 1

    # Show backup info
    meta = read_backup_meta(backup_path)
    if meta:
        print("\nBackup Information:")
        print(f"  Version: {meta.get('app_version', 'unknown')}")
        print(f"  Schema:  {meta.get('alembic_revision', 'unknown')}")
        suggested_tag = suggest_image_tag_from_meta(meta)
        if suggested_tag:
            print(f"  Suggested image: {suggested_tag}")

    # Check schema compatibility
    current_revision = get_alembic_head_revision()
    backup_revision = meta.get("alembic_revision") if meta else None
    if current_revision and backup_revision and current_revision != backup_revision:
        print("\nWARNING: Schema version mismatch!")
        print(f"  Current schema: {current_revision}")
        print(f"  Backup schema:  {backup_revision}")
        print("  This may cause issues. Consider using matching versions.")

        if not args.force:
            response = input("\nContinue anyway? [y/N]: ")
            if response.lower() != "y":
                print("Restore cancelled")
                return 1

    # Create pre-restore snapshot
    snapshot_path = None
    if not args.no_snapshot:
        db_path = config_dir / "researcharr.db"
        if db_path.exists():
            snapshot_path = (
                backups_dir / f"pre-restore-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.db"
            )
            print(f"\nCreating pre-restore snapshot: {snapshot_path.name}")
            if not snapshot_sqlite(db_path, snapshot_path):
                print("WARNING: Failed to create pre-restore snapshot", file=sys.stderr)
                if not args.force:
                    response = input("Continue without snapshot? [y/N]: ")
                    if response.lower() != "y":
                        print("Restore cancelled")
                        return 1
            else:
                print("✓ Snapshot created")

    # Perform restore
    print("\nRestoring backup...")
    try:
        success = restore_backup(backup_path, config_dir)
        if not success:
            print("\nERROR: Restore failed", file=sys.stderr)
            if snapshot_path and snapshot_path.exists():
                print(f"Pre-restore snapshot available at: {snapshot_path}")
            return 1

        print("✓ Restore completed successfully")

        # Verify database integrity
        db_path = config_dir / "researcharr.db"
        if db_path.exists():
            print("\nVerifying database integrity...")
            if check_db_integrity(db_path):
                print("✓ Database integrity check passed")
            else:
                print("WARNING: Database integrity check failed!", file=sys.stderr)
                if snapshot_path and snapshot_path.exists():
                    print(f"\nRollback snapshot available at: {snapshot_path}")
                    if args.auto_rollback:
                        print("Attempting automatic rollback...")
                        if snapshot_sqlite(snapshot_path, db_path):
                            print("✓ Rollback completed")
                        else:
                            print("ERROR: Rollback failed", file=sys.stderr)
                        return 1
                return 1

        # Clean up snapshot if restore was successful and auto-cleanup is enabled
        if snapshot_path and snapshot_path.exists() and args.cleanup_snapshot:
            print(f"\nRemoving pre-restore snapshot: {snapshot_path.name}")
            snapshot_path.unlink()

        return 0

    except Exception as e:  # nosec B110
        print(f"\nERROR: {e}", file=sys.stderr)
        if snapshot_path and snapshot_path.exists():
            print(f"Pre-restore snapshot available at: {snapshot_path}")
        return 1


def cmd_prune(args: argparse.Namespace) -> int:
    """Prune old backups according to retention policy."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)

    # Load retention policy from config or use defaults
    retention_config = {
        "retain_count": args.retain_count,
        "retain_days": args.retain_days,
        "pre_restore_keep_days": args.pre_restore_keep_days,
    }

    print(f"Pruning backups in: {backups_dir}")
    print("Retention policy:")
    print(f"  Keep count: {retention_config['retain_count']}")
    print(f"  Keep days:  {retention_config['retain_days']}")
    print(f"  Pre-restore keep days: {retention_config['pre_restore_keep_days']}")

    try:
        # List backups before pruning
        before = list_backups(backups_dir)
        before_count = len(before)

        prune_backups(backups_dir, retention_config)

        # List backups after pruning
        after = list_backups(backups_dir)
        after_count = len(after)

        removed = before_count - after_count
        print("\n✓ Pruning completed")
        print(f"  Removed: {removed} backup(s)")
        print(f"  Remaining: {after_count} backup(s)")

        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a backup file."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)
    backup_path = backups_dir / args.backup_name

    if not backup_path.exists():
        print(f"ERROR: Backup not found: {backup_path}", file=sys.stderr)
        return 1

    print(f"Validating: {backup_path.name}")

    try:
        is_valid = validate_backup_file(backup_path)

        if is_valid:
            print("✓ Backup is valid")
            return 0
        else:
            print("✗ Backup validation failed", file=sys.stderr)
            return 1

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed information about a backup."""
    config_dir = Path(args.config_dir) if args.config_dir else get_config_dir()
    backups_dir = get_backups_dir(config_dir)
    backup_path = backups_dir / args.backup_name

    if not backup_path.exists():
        print(f"ERROR: Backup not found: {backup_path}", file=sys.stderr)
        return 1

    try:
        info = get_backup_info(backup_path)
        if info is None:
            print("ERROR: Failed to read backup info", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(info, indent=2, default=str))
            return 0

        print(f"Backup: {backup_path.name}")
        print(f"Path: {backup_path}")
        print(f"Size: {format_size(get_backup_size(backup_path))}")
        print("\nMetadata:")

        meta = info.get("metadata", {})
        for key, value in meta.items():
            print(f"  {key}: {value}")

        files = info.get("files", [])
        if files:
            print(f"\nContents ({len(files)} files):")
            for file_info in files[:20]:  # Show first 20 files
                print(f"  {file_info}")
            if len(files) > 20:
                print(f"  ... and {len(files) - 20} more")

        # Additional compatibility info
        meta_dict = read_backup_meta(backup_path)
        if meta_dict:
            suggested_tag = suggest_image_tag_from_meta(meta_dict)
            if suggested_tag:
                print("\nCompatibility:")
                print(f"  Suggested image: {suggested_tag}")

            current_revision = get_alembic_head_revision()
            backup_revision = meta_dict.get("alembic_revision")
            if current_revision and backup_revision:
                if current_revision == backup_revision:
                    print(f"  Schema: ✓ Compatible (revision {current_revision})")
                else:
                    print("  Schema: ⚠ Mismatch")
                    print(f"    Current: {current_revision}")
                    print(f"    Backup:  {backup_revision}")

        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_health(args: argparse.Namespace) -> int:
    """Check application health."""
    try:
        health_service = MonitoringService()
        health = health_service.check_all_health()

        if args.json:
            print(json.dumps(health, indent=2))
            return 0

        print(f"Status: {health['status'].upper()}")
        print(f"Timestamp: {health.get('timestamp', 'N/A')}")

        components = health.get("components", {})
        if components:
            print("\nComponents:")
            for name, info in components.items():
                status = info.get("status", "unknown")
                icon = "✓" if status == "ok" else ("⚠" if status == "warning" else "✗")
                print(f"  {icon} {name}: {status}")
                if "error" in info:
                    print(f"      Error: {info['error']}")

        return 0 if health["status"] in ("ok", "warning") else 1

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_db_init(args: argparse.Namespace) -> int:
    """Initialize the database."""
    db_path = args.db_path or (get_config_dir() / "researcharr.db")

    print(f"Initializing database: {db_path}")

    try:
        db_service = DatabaseService(str(db_path))
        db_service.init_db()

        print("✓ Database initialized successfully")
        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_db_check(args: argparse.Namespace) -> int:
    """Check database integrity."""
    db_path = args.db_path or (get_config_dir() / "researcharr.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        return 1

    print(f"Checking database: {db_path}")

    try:
        if check_db_integrity(db_path):
            print("✓ Database integrity check passed")
            return 0
        else:
            print("✗ Database integrity check failed", file=sys.stderr)
            return 1

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_db_health(args: argparse.Namespace) -> int:
    """Check comprehensive database health."""
    db_path = args.db_path or (get_config_dir() / "researcharr.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        monitor = get_database_health_monitor(db_path)
        health = monitor.check_database_health()

        if args.json:
            print(json.dumps(health, indent=2))
        else:
            print("\nDatabase Health Status")
            print("=" * 50)
            print(f"Overall Status: {health['status'].upper()}")
            print(f"Database Path: {db_path}")
            print()

            # Display checks
            for check_name, check_data in health["checks"].items():
                status = check_data.get("status", "unknown")
                icon = "✓" if status == "ok" else ("⚠" if status == "warning" else "✗")
                print(f"{icon} {check_name.title()}: {status}")

                # Show relevant details
                if check_name == "connection":
                    if "latency_ms" in check_data:
                        print(f"    Latency: {check_data['latency_ms']}ms")
                elif check_name == "storage":
                    if "db_size_mb" in check_data:
                        print(f"    Database Size: {check_data['db_size_mb']}MB")
                    if "wal_size_mb" in check_data:
                        print(f"    WAL Size: {check_data['wal_size_mb']}MB")
                elif check_name == "performance":
                    if "query_latency_ms" in check_data:
                        print(f"    Query Latency: {check_data['query_latency_ms']}ms")
                    if "table_count" in check_data:
                        print(f"    Tables: {check_data['table_count']}")
                elif check_name == "schema":
                    if "migration_current" in check_data:
                        print(
                            f"    Migrations: {'current' if check_data['migration_current'] else 'pending'}"
                        )

                if "error" in check_data:
                    print(f"    Error: {check_data['error']}")
                if "message" in check_data:
                    print(f"    {check_data['message']}")
                print()

            # Display alerts
            if health.get("alerts"):
                print("\nAlerts:")
                for alert in health["alerts"]:
                    level = alert.get("level", "info").upper()
                    message = alert.get("message", "")
                    print(f"  [{level}] {message}")
                print()

        return 0 if health["status"] in ("ok", "warning") else 1

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_db_stats(args: argparse.Namespace) -> int:
    """Display database statistics."""
    db_path = args.db_path or (get_config_dir() / "researcharr.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        return 1

    try:
        monitor = get_database_health_monitor(db_path)
        stats = monitor.get_statistics()

        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\nDatabase Statistics")
            print("=" * 50)
            print(f"Database Path: {db_path}")
            print()

            if "table_counts" in stats:
                print("Table Row Counts:")
                for table, count in sorted(stats["table_counts"].items()):
                    if count >= 0:
                        print(f"  {table}: {count:,}")
                    else:
                        print(f"  {table}: ERROR")
                print()

            if "total_rows" in stats:
                print(f"Total Rows: {stats['total_rows']:,}")
                print()

            if "error" in stats:
                print(f"ERROR: {stats['error']}", file=sys.stderr)

        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_db_integrity(args: argparse.Namespace) -> int:
    """Run comprehensive integrity check."""
    db_path = args.db_path or (get_config_dir() / "researcharr.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        return 1

    print(f"Running integrity check on: {db_path}")
    print("This may take a few moments...")
    print()

    try:
        monitor = get_database_health_monitor(db_path)
        result = monitor.force_integrity_check()

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result.get("status", "unknown")
            icon = "✓" if status == "ok" else "✗"

            print(f"{icon} Integrity Check: {status.upper()}")

            if "check_time_ms" in result:
                print(f"Check completed in {result['check_time_ms']}ms")

            if "result" in result:
                print(f"Result: {result['result']}")

            if "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)

        return 0 if status == "ok" else 1

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_run_job(args: argparse.Namespace) -> int:
    """Run the scheduled job manually."""
    print("Running scheduled job...")

    try:
        # Debug: emit module identity information so we can verify tests patch
        # the exact module object the CLI is calling. This helps diagnose
        # intermittent failures where the test's mock isn't observing calls.
        try:
            mod_obj = sys.modules.get("researcharr.run")
            print(
                f"DEBUG: _run_module id={id(_run_module)} module(researcharr.run) id={id(mod_obj)}"
            )
            run_attr = getattr(_run_module, "run_job", None)
            print(f"DEBUG: run_job attr id={id(run_attr)} callable={callable(run_attr)}")
        except Exception:
            # Defensive: don't fail the CLI if debug printing has issues
            pass

        # Resolve the `researcharr.run` module from sys.modules at call time
        # so that tests which patch `researcharr.run.run_job` will be
        # observed even if there are multiple module objects loaded.
        mod_obj = sys.modules.get("researcharr.run")
        if mod_obj is None:
            # fall back to the module object cached at import time
            mod_obj = _run_module

        # Debug: show both ids to aid triage when duplicates occur
        try:
            print(
                f"DEBUG: _run_module id={id(_run_module)} module(researcharr.run) id={id(sys.modules.get('researcharr.run'))}"
            )
        except Exception:
            pass

        run_fn = getattr(mod_obj, "run_job", None)
        if not callable(run_fn):
            raise Exception("run_job not found on researcharr.run")

        run_fn()
        print("✓ Job completed successfully")
        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_config_show(args: argparse.Namespace) -> int:
    """Show current configuration."""
    config_path = args.config_path or (get_config_dir() / "config.yml")

    if not Path(config_path).exists():
        print(f"Configuration file not found: {config_path}")
        return 1

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if args.json:
            print(json.dumps(config, indent=2, default=str))
        else:
            print(yaml.dump(config, default_flow_style=False))

        return 0

    except Exception as e:  # nosec B110
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="ResearchArr Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check application health")
    health_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    health_parser.set_defaults(func=cmd_health)

    # Database command group
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_subparsers = db_parser.add_subparsers(dest="subcommand", help="Database subcommand")

    # db init
    db_init_parser = db_subparsers.add_parser("init", help="Initialize database")
    db_init_parser.add_argument(
        "--db-path",
        help="Database file path (default: $CONFIG_DIR/researcharr.db)",
    )
    db_init_parser.set_defaults(func=cmd_db_init)

    # db check
    db_check_parser = db_subparsers.add_parser("check", help="Check database integrity")
    db_check_parser.add_argument(
        "--db-path",
        help="Database file path (default: $CONFIG_DIR/researcharr.db)",
    )
    db_check_parser.set_defaults(func=cmd_db_check)

    # db health
    db_health_parser = db_subparsers.add_parser("health", help="Check database health")
    db_health_parser.add_argument(
        "--db-path",
        help="Database file path (default: $CONFIG_DIR/researcharr.db)",
    )
    db_health_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    db_health_parser.set_defaults(func=cmd_db_health)

    # db stats
    db_stats_parser = db_subparsers.add_parser("stats", help="Show database statistics")
    db_stats_parser.add_argument(
        "--db-path",
        help="Database file path (default: $CONFIG_DIR/researcharr.db)",
    )
    db_stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    db_stats_parser.set_defaults(func=cmd_db_stats)

    # db integrity
    db_integrity_parser = db_subparsers.add_parser(
        "integrity", help="Run comprehensive integrity check"
    )
    db_integrity_parser.add_argument(
        "--db-path",
        help="Database file path (default: $CONFIG_DIR/researcharr.db)",
    )
    db_integrity_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    db_integrity_parser.set_defaults(func=cmd_db_integrity)

    # Run command
    run_parser = subparsers.add_parser("run", help="Run scheduled job manually")
    run_parser.set_defaults(func=cmd_run_job)

    # Config command group
    config_parser = subparsers.add_parser("config", help="Configuration operations")
    config_subparsers = config_parser.add_subparsers(dest="subcommand", help="Config subcommand")

    # config show
    config_show_parser = config_subparsers.add_parser("show", help="Show configuration")
    config_show_parser.add_argument(
        "--config-path",
        help="Configuration file path (default: $CONFIG_DIR/config.yml)",
    )
    config_show_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    config_show_parser.set_defaults(func=cmd_config_show)

    # Backup command group
    backup_parser = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers = backup_parser.add_subparsers(dest="subcommand", help="Backup subcommand")

    # backup create
    create_parser = backup_subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    create_parser.add_argument(
        "--prefix",
        default="",
        help="Prefix for backup filename",
    )
    create_parser.set_defaults(func=cmd_create)

    # backup list
    list_parser = backup_subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    list_parser.add_argument(
        "--pattern",
        help="Filter backups by filename pattern",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    list_parser.set_defaults(func=cmd_list)

    # backup restore
    restore_parser = backup_subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_name", help="Backup filename to restore")
    restore_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    restore_parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip creating pre-restore snapshot",
    )
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts and warnings",
    )
    restore_parser.add_argument(
        "--auto-rollback",
        action="store_true",
        help="Automatically rollback on integrity check failure",
    )
    restore_parser.add_argument(
        "--cleanup-snapshot",
        action="store_true",
        help="Remove pre-restore snapshot after successful restore",
    )
    restore_parser.set_defaults(func=cmd_restore)

    # backup prune
    prune_parser = backup_subparsers.add_parser("prune", help="Prune old backups")
    prune_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    prune_parser.add_argument(
        "--retain-count",
        type=int,
        default=10,
        help="Number of recent backups to keep (default: 10)",
    )
    prune_parser.add_argument(
        "--retain-days",
        type=int,
        default=30,
        help="Keep backups newer than N days (default: 30)",
    )
    prune_parser.add_argument(
        "--pre-restore-keep-days",
        type=int,
        default=7,
        help="Keep pre-restore snapshots for N days (default: 7)",
    )
    prune_parser.set_defaults(func=cmd_prune)

    # backup validate
    validate_parser = backup_subparsers.add_parser("validate", help="Validate a backup file")
    validate_parser.add_argument("backup_name", help="Backup filename to validate")
    validate_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # backup info
    info_parser = backup_subparsers.add_parser("info", help="Show backup information")
    info_parser.add_argument("backup_name", help="Backup filename")
    info_parser.add_argument(
        "--config-dir",
        help="Configuration directory path (default: $CONFIG_DIR or /config)",
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
