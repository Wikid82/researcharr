"""Database health monitoring service.

Provides comprehensive database health checks including connectivity, integrity,
schema validation, performance metrics, and storage health monitoring.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseHealthMonitor:
    """Monitor database health with metrics, events, and periodic checks."""

    def __init__(
        self,
        db_path: str | Path,
        config: dict[str, Any] | None = None,
        event_bus: Any | None = None,
    ):
        """Initialize database health monitor.

        Args:
            db_path: Path to the SQLite database file
            config: Configuration dictionary with thresholds
            event_bus: Event bus for publishing health events
        """
        self.db_path = Path(db_path)
        self.config = config or {}
        self.event_bus = event_bus

        # Default thresholds (can be overridden in config)
        self.thresholds = {
            "size_warning_mb": self.config.get("db_size_warning_mb", 1000),  # 1GB
            "size_critical_mb": self.config.get("db_size_critical_mb", 5000),  # 5GB
            "query_latency_warning_ms": self.config.get("db_latency_warning_ms", 100),
            "query_latency_critical_ms": self.config.get("db_latency_critical_ms", 500),
            "wal_size_warning_mb": self.config.get("db_wal_warning_mb", 50),
            "integrity_check_interval_hours": self.config.get("db_integrity_interval_hours", 24),
        }

        # Initialize metrics
        self._metrics = {
            "connection_ok": False,
            "last_check_timestamp": None,
            "last_integrity_check": None,
            "integrity_ok": None,
            "db_size_bytes": 0,
            "wal_size_bytes": 0,
            "query_latency_ms": 0.0,
            "table_count": 0,
            "total_rows": 0,
            "failed_checks": 0,
            "checks_performed": 0,
        }

    def check_database_health(self) -> dict[str, Any]:
        """Perform comprehensive database health check.

        Returns:
            Dictionary with health status and detailed checks
        """
        self._metrics["checks_performed"] += 1
        self._metrics["last_check_timestamp"] = time.time()

        health = {
            "status": "ok",
            "timestamp": time.time(),
            "checks": {},
            "alerts": [],
        }

        # Perform individual checks
        connection_result = self._check_connection()
        health["checks"]["connection"] = connection_result
        if connection_result["status"] != "ok":
            health["status"] = "error"
            health["alerts"].append(
                {
                    "level": "error",
                    "message": "Database connection failed",
                    "check": "connection",
                }
            )
            self._publish_event(
                "DB_HEALTH_CHECK_FAILED",
                {
                    "check": "connection",
                    "error": connection_result.get("error"),
                },
            )

        storage_result = self._check_storage()
        health["checks"]["storage"] = storage_result
        if storage_result["status"] == "critical":
            health["status"] = "error"
            health["alerts"].append(
                {
                    "level": "error",
                    "message": storage_result.get("message", "Storage critical"),
                    "check": "storage",
                }
            )
        elif storage_result["status"] == "warning":
            if health["status"] == "ok":
                health["status"] = "warning"
            health["alerts"].append(
                {
                    "level": "warning",
                    "message": storage_result.get("message", "Storage warning"),
                    "check": "storage",
                }
            )

        performance_result = self._check_performance()
        health["checks"]["performance"] = performance_result
        if performance_result["status"] == "critical":
            health["status"] = "error"
            health["alerts"].append(
                {
                    "level": "error",
                    "message": "Database performance critical",
                    "check": "performance",
                }
            )
        elif performance_result["status"] == "warning":
            if health["status"] == "ok":
                health["status"] = "warning"
            health["alerts"].append(
                {
                    "level": "warning",
                    "message": "Database performance degraded",
                    "check": "performance",
                }
            )

        # Integrity check (may be skipped if recent)
        integrity_result = self._check_integrity(force=False)
        health["checks"]["integrity"] = integrity_result
        if integrity_result.get("checked") and integrity_result["status"] != "ok":
            health["status"] = "error"
            health["alerts"].append(
                {
                    "level": "error",
                    "message": "Database integrity check failed",
                    "check": "integrity",
                }
            )
            self._publish_event(
                "DB_INTEGRITY_FAILED",
                {
                    "db_path": str(self.db_path),
                },
            )

        schema_result = self._check_schema()
        health["checks"]["schema"] = schema_result
        if schema_result["status"] == "warning":
            if health["status"] == "ok":
                health["status"] = "warning"
            health["alerts"].append(
                {
                    "level": "warning",
                    "message": schema_result.get("message", "Schema warning"),
                    "check": "schema",
                }
            )

        # Update overall metrics
        if health["status"] != "ok":
            self._metrics["failed_checks"] += 1

        # Publish health check event
        self._publish_event(
            "DB_HEALTH_CHECK",
            {
                "status": health["status"],
                "alerts_count": len(health["alerts"]),
            },
        )

        return health

    def _check_connection(self) -> dict[str, Any]:
        """Check database connection and measure latency."""
        try:
            start = time.time()
            con = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                con.execute("SELECT 1")
                latency_ms = (time.time() - start) * 1000
                self._metrics["connection_ok"] = True
                self._metrics["query_latency_ms"] = latency_ms

                status = "ok"
                if latency_ms >= self.thresholds["query_latency_critical_ms"]:
                    status = "critical"
                elif latency_ms >= self.thresholds["query_latency_warning_ms"]:
                    status = "warning"

                return {
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "path": str(self.db_path),
                }
            finally:
                con.close()
        except Exception as e:
            self._metrics["connection_ok"] = False
            logger.exception("Database connection check failed")
            return {
                "status": "error",
                "error": str(e),
                "path": str(self.db_path),
            }

    def _check_storage(self) -> dict[str, Any]:
        """Check database file size and storage metrics."""
        try:
            if not self.db_path.exists():
                return {
                    "status": "error",
                    "error": "Database file not found",
                }

            db_size = self.db_path.stat().st_size
            self._metrics["db_size_bytes"] = db_size
            db_size_mb = db_size / (1024 * 1024)

            # Check WAL file if exists
            wal_path = self.db_path.with_suffix(self.db_path.suffix + "-wal")
            wal_size = 0
            if wal_path.exists():
                wal_size = wal_path.stat().st_size
                self._metrics["wal_size_bytes"] = wal_size

            wal_size_mb = wal_size / (1024 * 1024)

            # Determine status based on thresholds
            status = "ok"
            message = None
            if db_size_mb >= self.thresholds["size_critical_mb"]:
                status = "critical"
                message = f"Database size {db_size_mb:.1f}MB exceeds critical threshold"
            elif db_size_mb >= self.thresholds["size_warning_mb"]:
                status = "warning"
                message = f"Database size {db_size_mb:.1f}MB exceeds warning threshold"
            elif wal_size_mb >= self.thresholds["wal_size_warning_mb"]:
                status = "warning"
                message = f"WAL size {wal_size_mb:.1f}MB is large"

            result = {
                "status": status,
                "db_size_mb": round(db_size_mb, 2),
                "wal_size_mb": round(wal_size_mb, 2),
            }
            if message:
                result["message"] = message

            if status in {"warning", "critical"}:
                self._publish_event(
                    "DB_SIZE_WARNING",
                    {
                        "db_size_mb": db_size_mb,
                        "wal_size_mb": wal_size_mb,
                        "threshold_mb": self.thresholds["size_warning_mb"],
                    },
                )

            return result

        except Exception as e:
            logger.exception("Storage check failed")
            return {
                "status": "error",
                "error": str(e),
            }

    def _check_performance(self) -> dict[str, Any]:
        """Check database performance metrics."""
        try:
            con = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                # Get page count and size
                cur = con.execute("PRAGMA page_count")
                page_count = cur.fetchone()[0] if cur else 0

                cur = con.execute("PRAGMA page_size")
                page_size = cur.fetchone()[0] if cur else 0

                # Check WAL mode
                cur = con.execute("PRAGMA journal_mode")
                journal_mode = cur.fetchone()[0] if cur else "unknown"

                # Get table count
                cur = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cur.fetchone()[0] if cur else 0
                self._metrics["table_count"] = table_count

                latency = self._metrics.get("query_latency_ms", 0)
                status = "ok"
                message = None

                if latency >= self.thresholds["query_latency_critical_ms"]:
                    status = "critical"
                    message = f"Query latency {latency:.1f}ms is critical"
                    self._publish_event(
                        "DB_PERFORMANCE_DEGRADED",
                        {
                            "latency_ms": latency,
                            "threshold_ms": self.thresholds["query_latency_critical_ms"],
                        },
                    )
                elif latency >= self.thresholds["query_latency_warning_ms"]:
                    status = "warning"
                    message = f"Query latency {latency:.1f}ms is elevated"

                result = {
                    "status": status,
                    "query_latency_ms": round(latency, 2),
                    "page_count": page_count,
                    "page_size": page_size,
                    "journal_mode": journal_mode,
                    "table_count": table_count,
                }
                if message:
                    result["message"] = message

                return result

            finally:
                con.close()

        except Exception as e:
            logger.exception("Performance check failed")
            return {
                "status": "error",
                "error": str(e),
            }

    def _check_integrity(self, force: bool = False) -> dict[str, Any]:
        """Check database integrity using PRAGMA integrity_check.

        Args:
            force: Force check even if recently performed

        Returns:
            Dictionary with integrity check results
        """
        # Skip if recently checked (unless forced)
        if not force and self._metrics.get("last_integrity_check"):
            hours_since_check = (time.time() - self._metrics["last_integrity_check"]) / 3600
            if hours_since_check < self.thresholds["integrity_check_interval_hours"]:
                return {
                    "status": self._metrics.get("integrity_ok", "unknown"),
                    "checked": False,
                    "last_check_hours_ago": round(hours_since_check, 1),
                }

        try:
            con = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                start = time.time()
                cur = con.execute("PRAGMA integrity_check")
                result = cur.fetchone()
                check_time = time.time() - start

                is_ok = result and result[0] == "ok"
                self._metrics["integrity_ok"] = is_ok
                self._metrics["last_integrity_check"] = time.time()

                return {
                    "status": "ok" if is_ok else "error",
                    "checked": True,
                    "result": result[0] if result else "unknown",
                    "check_time_ms": round(check_time * 1000, 2),
                }

            finally:
                con.close()

        except Exception as e:
            logger.exception("Integrity check failed")
            self._metrics["integrity_ok"] = False
            self._metrics["last_integrity_check"] = time.time()
            return {
                "status": "error",
                "checked": True,
                "error": str(e),
            }

    def _check_schema(self) -> dict[str, Any]:
        """Check database schema health."""
        try:
            # Check migration status
            migration_status = self._check_migrations()

            # Get table list
            con = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cur.fetchall()]

                # Expected core tables
                expected_tables = {"global_settings", "managed_apps", "tracked_items"}
                missing_tables = expected_tables - set(tables)

                status = "ok"
                message = None

                if missing_tables:
                    status = "warning"
                    message = f"Missing expected tables: {', '.join(missing_tables)}"
                elif not migration_status.get("current", True):
                    status = "warning"
                    message = "Database migrations pending"
                    self._publish_event(
                        "DB_MIGRATION_PENDING",
                        {
                            "current": migration_status.get("current_revision"),
                            "head": migration_status.get("head_revision"),
                        },
                    )

                result = {
                    "status": status,
                    "tables": tables,
                    "table_count": len(tables),
                    "migration_current": migration_status.get("current", True),
                }
                if message:
                    result["message"] = message

                return result

            finally:
                con.close()

        except Exception as e:
            logger.exception("Schema check failed")
            return {
                "status": "error",
                "error": str(e),
            }

    def _check_migrations(self) -> dict[str, Any]:
        """Check Alembic migration status."""
        try:
            from researcharr.storage.recovery import get_alembic_head_revision

            head_revision = get_alembic_head_revision()

            # Try to get current revision from database
            try:
                con = sqlite3.connect(str(self.db_path), timeout=5.0)
                try:
                    cur = con.execute(
                        "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
                    )
                    row = cur.fetchone()
                    current_revision = row[0] if row else None
                finally:
                    con.close()
            except Exception:
                current_revision = None

            is_current = (
                head_revision is None
                or current_revision is None
                or head_revision == current_revision
            )

            return {
                "current": is_current,
                "current_revision": current_revision,
                "head_revision": head_revision,
            }

        except Exception as e:
            logger.warning(f"Migration check failed: {e}")
            return {
                "current": True,  # Assume ok if check fails
                "error": str(e),
            }

    def get_metrics(self) -> dict[str, Any]:
        """Get current database health metrics.

        Returns:
            Dictionary with all tracked metrics
        """
        return self._metrics.copy()

    def get_statistics(self) -> dict[str, Any]:
        """Get detailed database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            con = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                stats: dict[str, Any] = {}

                # Get row counts per table
                cur = con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row[0] for row in cur.fetchall()]

                table_counts = {}
                total_rows = 0
                for table in tables:
                    try:
                        cur = con.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                        count = cur.fetchone()[0]
                        table_counts[table] = count
                        total_rows += count
                    except Exception:
                        table_counts[table] = -1  # Error getting count

                self._metrics["total_rows"] = total_rows

                stats["table_counts"] = table_counts
                stats["total_rows"] = total_rows

                # Get database info
                cur = con.execute("PRAGMA database_list")
                db_info = cur.fetchall()
                stats["databases"] = [
                    {"seq": row[0], "name": row[1], "file": row[2]} for row in db_info
                ]

                return stats

            finally:
                con.close()

        except Exception as e:
            logger.exception("Failed to get database statistics")
            return {"error": str(e)}

    def force_integrity_check(self) -> dict[str, Any]:
        """Force immediate integrity check regardless of interval.

        Returns:
            Integrity check results
        """
        return self._check_integrity(force=True)

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish event to event bus.

        Args:
            event_type: Event type/name
            data: Event data
        """
        if not self.event_bus:
            return

        try:
            full_event = {
                "type": event_type,
                "timestamp": time.time(),
                "db_path": str(self.db_path),
                **data,
            }
            self.event_bus.publish_simple(event_type, data=full_event, source="database_monitor")
        except Exception as e:
            logger.warning(f"Failed to publish event {event_type}: {e}")


def get_database_health_monitor(
    db_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> DatabaseHealthMonitor:
    """Get or create database health monitor instance.

    Args:
        db_path: Path to database (defaults to RESEARCHARR_DB env var)
        config: Configuration dictionary

    Returns:
        DatabaseHealthMonitor instance
    """
    if db_path is None:
        db_path = os.getenv("RESEARCHARR_DB", "researcharr.db")

    try:
        from researcharr.core.events import get_event_bus

        event_bus = get_event_bus()
    except Exception:
        event_bus = None

    return DatabaseHealthMonitor(db_path, config, event_bus)
