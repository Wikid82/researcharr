"""Additional tests for ProcessingLogRepository cleanup edge cases."""

from datetime import datetime, timedelta

from researcharr.repositories.processing_log import ProcessingLogRepository
from researcharr.storage.database import get_session, init_db
from researcharr.storage.models import AppType, ManagedApp, ProcessingLog


def _setup_session(tmp_path):
    init_db(tmp_path / "proc.db")
    return get_session()


def test_cleanup_old_logs_deletes_expected(tmp_path):
    with _setup_session(tmp_path) as session:
        app = ManagedApp(app_type=AppType.RADARR, name="App", base_url="http://x", api_key="k")
        session.add(app)
        session.flush()
        repo = ProcessingLogRepository(session)
        # Create one old and one recent log
        old = ProcessingLog(app_id=app.id, event_type="e", message="old", success=True)
        old.created_at = datetime.utcnow() - timedelta(days=40)
        recent = ProcessingLog(app_id=app.id, event_type="e", message="recent", success=True)
        session.add_all([old, recent])
        session.flush()
        deleted = repo.cleanup_old_logs(days=30)
        assert deleted == 1
    with get_session() as session:
        remaining = session.query(ProcessingLog).count()
        assert remaining == 1


def test_cleanup_no_deletes_when_within_window(tmp_path):
    with _setup_session(tmp_path) as session:
        app = ManagedApp(app_type=AppType.RADARR, name="App2", base_url="http://y", api_key="k")
        session.add(app)
        session.flush()
        repo = ProcessingLogRepository(session)
        # All logs within retention window
        for i in range(3):
            log = ProcessingLog(app_id=app.id, event_type="e", message=f"log-{i}", success=True)
            log.created_at = datetime.utcnow() - timedelta(days=5)
            session.add(log)
        session.flush()
        deleted = repo.cleanup_old_logs(days=30)
        assert deleted == 0
