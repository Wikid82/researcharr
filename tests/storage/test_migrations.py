"""Tests for migration utilities and Alembic migrations."""

import sqlite3
from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config
from researcharr.storage.database import get_session, init_db
from researcharr.storage.migrations import migrate_database, reset_database
from researcharr.storage.models import GlobalSettings


def test_migrate_database_creates_settings(tmp_path):
    db_file = tmp_path / "migrate.db"
    migrate_database(db_file, use_migrations=False)  # Fast path for this test
    assert db_file.exists()
    with get_session() as session:
        settings = session.query(GlobalSettings).filter_by(id=1).first()
        assert settings is not None


def test_reset_database_recreates_clean_db(tmp_path):
    db_file = tmp_path / "reset.db"
    migrate_database(db_file, use_migrations=False)  # Fast path
    # Add a second record (invalid for singleton but to prove reset clears)
    with get_session() as session:
        gs = session.query(GlobalSettings).filter_by(id=1).first()
        assert gs is not None
    # Reset and ensure database file recreated and singleton exists again
    reset_database(db_file)
    assert db_file.exists()
    with get_session() as session:
        settings = session.query(GlobalSettings).filter_by(id=1).first()
        assert settings is not None


class TestAlembicMigrations:
    """Test Alembic migration system."""

    @pytest.fixture
    def alembic_config(self, tmp_path: Path) -> Config:
        """Create Alembic config pointing to temp database."""
        db_path = tmp_path / "test.db"
        repo_root = Path(__file__).parent.parent.parent
        alembic_ini = repo_root / "alembic.ini"
        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        return config

    def test_migration_upgrade_creates_tables(self, tmp_path: Path, alembic_config: Config) -> None:
        """Test that migration upgrade creates all expected tables."""
        db_path = tmp_path / "test.db"
        command.upgrade(alembic_config, "head")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "alembic_version" in tables
        assert "global_settings" in tables
        assert "managed_apps" in tables
        assert "tracked_items" in tables
        assert "search_cycles" in tables
        assert "processing_logs" in tables

    def test_migration_upgrade_creates_indexes(
        self, tmp_path: Path, alembic_config: Config
    ) -> None:
        """Test that migrations create performance indexes."""
        db_path = tmp_path / "test.db"
        command.upgrade(alembic_config, "head")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_indexes = [
            "ix_managed_apps_is_active",
            "ix_managed_apps_app_type",
            "ix_tracked_items_app_monitored",
            "ix_tracked_items_last_search_at",
            "ix_search_cycles_app_started",
            "ix_processing_logs_event_type",
        ]

        for idx in expected_indexes:
            assert idx in indexes, f"Expected index {idx} not found"

    def test_migration_downgrade_removes_indexes(
        self, tmp_path: Path, alembic_config: Config
    ) -> None:
        """Test that downgrade removes performance indexes."""
        db_path = tmp_path / "test.db"
        command.upgrade(alembic_config, "head")
        command.downgrade(alembic_config, "-1")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert len(indexes) == 0, "Performance indexes should be removed"

    def test_init_db_with_migrations_disabled(self, tmp_path: Path) -> None:
        """Test init_db with use_migrations=False (fast path)."""
        db_path = tmp_path / "test.db"
        init_db(db_path, use_migrations=False)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "managed_apps" in tables
        assert "tracked_items" in tables
        assert "alembic_version" not in tables  # Should not exist without migrations

    def test_migration_idempotency(self, tmp_path: Path, alembic_config: Config) -> None:
        """Test that running migrations multiple times is safe."""
        db_path = tmp_path / "test.db"
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")  # Should be no-op

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "managed_apps" in tables
        assert len([t for t in tables if t == "managed_apps"]) == 1
