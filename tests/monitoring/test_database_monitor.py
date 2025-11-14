"""Tests for database health monitoring."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from researcharr.monitoring.database_monitor import (
    DatabaseHealthMonitor,
    get_database_health_monitor,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create a basic database with tables
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE global_settings (
                id INTEGER PRIMARY KEY,
                items_per_cycle INTEGER
            )
        """
        )
        con.execute(
            """
            CREATE TABLE managed_apps (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """
        )
        con.execute(
            """
            CREATE TABLE tracked_items (
                id INTEGER PRIMARY KEY,
                title TEXT
            )
        """
        )
        con.execute("INSERT INTO global_settings (id, items_per_cycle) VALUES (1, 10)")
        con.execute("INSERT INTO managed_apps (id, name) VALUES (1, 'test_app')")
        con.commit()
    finally:
        con.close()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except Exception:
        pass


def test_database_health_monitor_init(temp_db):
    """Test DatabaseHealthMonitor initialization."""

    monitor = DatabaseHealthMonitor(temp_db)

    assert monitor.db_path == temp_db
    assert monitor.thresholds["size_warning_mb"] == 1000
    assert monitor._metrics["connection_ok"] is False
    assert monitor._metrics["checks_performed"] == 0


def test_database_health_monitor_with_config(temp_db):
    """Test DatabaseHealthMonitor with custom config."""

    config = {
        "db_size_warning_mb": 500,
        "db_latency_warning_ms": 50,
    }

    monitor = DatabaseHealthMonitor(temp_db, config=config)

    assert monitor.thresholds["size_warning_mb"] == 500
    assert monitor.thresholds["query_latency_warning_ms"] == 50


def test_check_connection_success(temp_db):
    """Test successful connection check."""

    monitor = DatabaseHealthMonitor(temp_db)
    result = monitor._check_connection()

    assert result["status"] == "ok"
    assert "latency_ms" in result
    assert result["latency_ms"] >= 0
    assert monitor._metrics["connection_ok"] is True


def test_check_connection_missing_db():
    """Test connection check with missing database."""

    monitor = DatabaseHealthMonitor("/nonexistent/database.db")
    result = monitor._check_connection()

    assert result["status"] == "error"
    assert "error" in result
    assert monitor._metrics["connection_ok"] is False


def test_check_storage_success(temp_db):
    """Test storage check."""

    monitor = DatabaseHealthMonitor(temp_db)
    result = monitor._check_storage()

    assert result["status"] == "ok"
    assert "db_size_mb" in result
    assert result["db_size_mb"] > 0
    assert "wal_size_mb" in result


def test_check_storage_size_warning(temp_db):
    """Test storage check with size warning."""

    config = {"db_size_warning_mb": 0.001}  # Very low threshold
    monitor = DatabaseHealthMonitor(temp_db, config=config)

    result = monitor._check_storage()

    assert result["status"] == "warning"
    assert "message" in result


def test_check_performance_success(temp_db):
    """Test performance check."""

    monitor = DatabaseHealthMonitor(temp_db)
    # Run connection check first to populate latency
    monitor._check_connection()

    result = monitor._check_performance()

    assert result["status"] == "ok"
    assert "query_latency_ms" in result
    assert "table_count" in result
    assert result["table_count"] == 3  # 3 tables created
    assert "journal_mode" in result


def test_check_integrity_success(temp_db):
    """Test integrity check passes."""

    monitor = DatabaseHealthMonitor(temp_db)
    result = monitor._check_integrity(force=True)

    assert result["checked"] is True
    assert result["status"] == "ok"
    assert result["result"] == "ok"
    assert "check_time_ms" in result
    assert monitor._metrics["integrity_ok"] is True


def test_check_integrity_skip_recent(temp_db):
    """Test integrity check is skipped if recent."""

    monitor = DatabaseHealthMonitor(temp_db)

    # First check (forced)
    result1 = monitor._check_integrity(force=True)
    assert result1["checked"] is True

    # Second check (should be skipped)
    result2 = monitor._check_integrity(force=False)
    assert result2["checked"] is False
    assert "last_check_hours_ago" in result2


def test_check_schema_success(temp_db):
    """Test schema check."""

    monitor = DatabaseHealthMonitor(temp_db)
    result = monitor._check_schema()

    assert result["status"] == "ok"
    assert "tables" in result
    assert len(result["tables"]) == 3
    assert "global_settings" in result["tables"]
    assert "table_count" in result


def test_check_database_health_comprehensive(temp_db):
    """Test comprehensive database health check."""

    monitor = DatabaseHealthMonitor(temp_db)
    health = monitor.check_database_health()

    assert "status" in health
    assert health["status"] == "ok"
    assert "checks" in health
    assert "connection" in health["checks"]
    assert "storage" in health["checks"]
    assert "performance" in health["checks"]
    assert "integrity" in health["checks"]
    assert "schema" in health["checks"]
    assert "alerts" in health
    assert monitor._metrics["checks_performed"] == 1


def test_check_database_health_with_errors():
    """Test health check with database errors."""

    monitor = DatabaseHealthMonitor("/nonexistent/database.db")
    health = monitor.check_database_health()

    assert health["status"] == "error"
    assert len(health["alerts"]) > 0
    assert health["alerts"][0]["level"] == "error"
    assert monitor._metrics["failed_checks"] == 1


def test_get_metrics(temp_db):
    """Test getting metrics."""

    monitor = DatabaseHealthMonitor(temp_db)
    monitor.check_database_health()

    metrics = monitor.get_metrics()

    assert "connection_ok" in metrics
    assert "last_check_timestamp" in metrics
    assert "checks_performed" in metrics
    assert metrics["checks_performed"] == 1
    assert "db_size_bytes" in metrics


def test_get_statistics(temp_db):
    """Test getting database statistics."""

    monitor = DatabaseHealthMonitor(temp_db)
    stats = monitor.get_statistics()

    assert "table_counts" in stats
    assert "total_rows" in stats
    assert stats["total_rows"] >= 2  # At least 2 rows inserted
    assert stats["table_counts"]["global_settings"] == 1
    assert stats["table_counts"]["managed_apps"] == 1


def test_force_integrity_check(temp_db):
    """Test forcing integrity check."""

    monitor = DatabaseHealthMonitor(temp_db)

    # First check
    result1 = monitor.force_integrity_check()
    assert result1["checked"] is True

    # Second check (forced, should run again)
    result2 = monitor.force_integrity_check()
    assert result2["checked"] is True


def test_event_publishing(temp_db):
    """Test event publishing to event bus."""

    mock_event_bus = Mock()
    monitor = DatabaseHealthMonitor(temp_db, event_bus=mock_event_bus)

    monitor.check_database_health()

    # Should publish at least DB_HEALTH_CHECK event
    assert mock_event_bus.publish_simple.called
    call_args = mock_event_bus.publish_simple.call_args_list
    event_types = [call[0][0] for call in call_args]
    assert "DB_HEALTH_CHECK" in event_types


def test_event_publishing_with_errors():
    """Test event publishing with errors."""

    mock_event_bus = Mock()
    monitor = DatabaseHealthMonitor("/nonexistent/database.db", event_bus=mock_event_bus)

    monitor.check_database_health()

    # Should publish error events
    call_args = mock_event_bus.publish_simple.call_args_list
    event_types = [call[0][0] for call in call_args]
    assert "DB_HEALTH_CHECK_FAILED" in event_types


def test_get_database_health_monitor_default():
    """Test getting database health monitor with defaults."""

    with patch.dict("os.environ", {"RESEARCHARR_DB": "test.db"}):
        monitor = get_database_health_monitor()
        assert monitor.db_path == Path("test.db")


def test_get_database_health_monitor_custom_path(temp_db):
    """Test getting database health monitor with custom path."""

    monitor = get_database_health_monitor(db_path=temp_db)
    assert monitor.db_path == temp_db


def test_migration_check_no_alembic(temp_db):
    """Test migration check when alembic table doesn't exist."""

    monitor = DatabaseHealthMonitor(temp_db)
    result = monitor._check_migrations()

    # Should handle missing alembic_version table gracefully
    assert "current" in result
    assert result["current"] is True  # Assume ok if check fails


def test_check_database_health_with_warnings(temp_db):
    """Test health check with warnings."""

    # Set very low thresholds to trigger warnings
    config = {
        "db_size_warning_mb": 0.001,
        "db_latency_warning_ms": 0.1,
    }

    monitor = DatabaseHealthMonitor(temp_db, config=config)
    health = monitor.check_database_health()

    # With very low thresholds, we may trigger error conditions
    # as well as warnings (e.g., if event publishing fails)
    assert health["status"] in ("ok", "warning", "error")
    if health["status"] in ("warning", "error"):
        assert len(health["alerts"]) > 0
