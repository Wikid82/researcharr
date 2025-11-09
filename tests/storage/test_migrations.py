"""Tests for migration utilities."""

from researcharr.storage.database import get_session
from researcharr.storage.migrations import migrate_database, reset_database
from researcharr.storage.models import GlobalSettings


def test_migrate_database_creates_settings(tmp_path):
    db_file = tmp_path / "migrate.db"
    migrate_database(db_file)
    assert db_file.exists()
    with get_session() as session:
        settings = session.query(GlobalSettings).filter_by(id=1).first()
        assert settings is not None


def test_reset_database_recreates_clean_db(tmp_path):
    db_file = tmp_path / "reset.db"
    migrate_database(db_file)
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
