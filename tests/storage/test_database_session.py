"""Tests for database session management utilities."""

from pathlib import Path
import pytest

from researcharr.storage.database import init_db, get_session, _session_factory  # type: ignore
from researcharr.storage.models import GlobalSettings


def test_get_session_requires_init(tmp_path):
    """get_session should raise before init_db is called.

    Reset _session_factory to None to simulate fresh start.
    """
    # Force reset of module-level session factory (test isolation)
    import researcharr.storage.database as dbmod

    dbmod._session_factory = None  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError):
        with get_session():  # type: ignore
            pass


def test_init_db_creates_directory_and_tables(tmp_path):
    """init_db should create parent directory and allow CRUD operations."""
    db_file = tmp_path / "nested" / "app.db"
    assert not db_file.parent.exists()
    init_db(str(db_file))
    assert db_file.parent.exists()
    assert db_file.exists()
    # Basic CRUD via session context manager (commit path)
    with get_session() as session:
        gs = GlobalSettings(id=1)
        session.add(gs)
    # Verify persisted
    with get_session() as session:
        found = session.query(GlobalSettings).filter_by(id=1).first()
        assert found is not None
        assert found.items_per_cycle == 5


def test_session_rollback_on_exception(tmp_path):
    """An exception inside the context should rollback the transaction."""
    init_db(tmp_path / "rollback.db")
    try:
        with get_session() as session:
            session.add(GlobalSettings(id=1))
            raise ValueError("trigger rollback")
    except ValueError:
        pass
    # Ensure row not committed
    with get_session() as session:
        assert session.query(GlobalSettings).filter_by(id=1).first() is None
