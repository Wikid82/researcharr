"""Tests for DB-level CHECK constraints introduced in migration 002_data_constraints.

These tests run only with migrations enabled to ensure constraints exist
and that violating rows trigger IntegrityError.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from researcharr.storage.database import get_engine, get_session
from researcharr.storage.migrations import migrate_database
from researcharr.storage.models import (
    CyclePhase,
    ManagedApp,
    ProcessingLog,
    SearchCycle,
    TrackedItem,
)


@pytest.fixture()
def migrated_db(tmp_path: Path):
    db_file = tmp_path / "constraints.db"
    migrate_database(db_file, use_migrations=True)
    yield db_file


def test_tracked_items_non_negative_constraints(migrated_db: Path):
    with get_session() as session:
        app = ManagedApp(app_type="radarr", name="Test", base_url="http://x", api_key="k")
        session.add(app)
        session.flush()
        ti = TrackedItem(
            app_id=app.id,
            arr_id=1,
            title="Item",
            monitored=True,
            has_file=False,
            custom_format_score=0.0,
            search_count=0,
            failed_search_count=0,
        )
        session.add(ti)
        session.flush()  # baseline OK
        ti.failed_search_count = -1
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_search_cycle_temporal_and_counts_constraints(migrated_db: Path):
    with get_session() as session:
        app = ManagedApp(app_type="radarr", name="App", base_url="http://x", api_key="k")
        session.add(app)
        session.flush()
        sc = SearchCycle(
            app_id=app.id,
            cycle_number=1,
            phase=CyclePhase.SYNCING,
            total_items=0,
            items_searched=0,
            items_succeeded=0,
            items_failed=0,
            items_in_retry_queue=0,
        )
        session.add(sc)
        session.flush()
        sc.items_failed = -5
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_processing_log_message_and_event_type_constraints(migrated_db: Path):
    with get_session() as session:
        app = ManagedApp(app_type="radarr", name="App", base_url="http://x", api_key="k")
        session.add(app)
        session.flush()
        log = ProcessingLog(app_id=app.id, event_type="evt", message="hello", success=True)
        session.add(log)
        session.flush()
        log.event_type = "x" * 60  # exceeds 50 char check
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_managed_app_non_empty_checks(migrated_db: Path):
    engine = get_engine()
    # Direct insert with blank name should violate constraint
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO managed_apps (app_type,name,base_url,api_key,is_active,use_custom_settings,created_at,updated_at) "
                    "VALUES (:app_type,'   ',:base_url,:api_key,1,0,datetime('now'),datetime('now'))"
                ),
                {"app_type": "radarr", "base_url": "http://x", "api_key": "k"},
            )
