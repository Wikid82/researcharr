"""Additional tests for ProcessingLogRepository cleanup edge cases."""

from datetime import datetime, timedelta

from researcharr.repositories.processing_log import ProcessingLogRepository
from researcharr.storage.database import get_session, init_db
from researcharr.storage.models import AppType, ManagedApp, ProcessingLog
from researcharr import cache as _cache
from researcharr.storage import database as _db
import os
import logging


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

    # Tear down global in-process state to avoid leaking DB/cache into later tests
    try:
        _cache.clear_all()
        _cache.reset_metrics()
    except Exception:
        pass
    try:
        if getattr(_db, "_engine", None) is not None:
            try:
                _db._engine.dispose()
            except Exception:
                pass
            _db._engine = None
            _db._session_factory = None
    except Exception:
        pass
    # Reset researcharr and logging manager state so caplog works
    try:
        # Clear researcharr.cron handlers and restore propagation/level
        l = logging.getLogger("researcharr.cron")
        l.handlers[:] = []
        l.filters[:] = [] if getattr(l, "filters", None) is not None else []
        l.propagate = True
        l.setLevel(logging.NOTSET)
        # For any logger under the researcharr namespace, clear handlers/filters
        lm = logging.root.manager
        for name, entry in list(lm.loggerDict.items()):
            if not isinstance(name, str):
                continue
            if name == "researcharr" or name.startswith("researcharr."):
                try:
                    logger = logging.getLogger(name)
                    logger.handlers[:] = []
                    if getattr(logger, "filters", None) is not None:
                        logger.filters[:] = []
                    logger.propagate = True
                    logger.setLevel(logging.NOTSET)
                    logger.disabled = False
                except Exception:
                    pass
    except Exception:
        pass
    # Reset Prometheus default registry to an empty CollectorRegistry to avoid
    # previously-registered collectors leaking between tests.
    try:
        from prometheus_client import core as prom_core
        try:
            prom_core.REGISTRY = prom_core.CollectorRegistry()
        except Exception:
            # best-effort: ignore if CollectorRegistry not available or reassignment fails
            pass
    except Exception:
        pass


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

    # Tear down state after test to avoid cross-test contamination
    try:
        _cache.clear_all()
        _cache.reset_metrics()
    except Exception:
        pass
    try:
        if getattr(_db, "_engine", None) is not None:
            try:
                _db._engine.dispose()
            except Exception:
                pass
            _db._engine = None
            _db._session_factory = None
    except Exception:
        pass
    try:
        l = logging.getLogger("researcharr.cron")
        l.handlers[:] = []
        l.filters[:] = [] if getattr(l, "filters", None) is not None else []
        l.propagate = True
        l.setLevel(logging.NOTSET)
        lm = logging.root.manager
        for name, entry in list(lm.loggerDict.items()):
            if not isinstance(name, str):
                continue
            if name == "researcharr" or name.startswith("researcharr."):
                try:
                    logger = logging.getLogger(name)
                    logger.handlers[:] = []
                    if getattr(logger, "filters", None) is not None:
                        logger.filters[:] = []
                    logger.propagate = True
                    logger.setLevel(logging.NOTSET)
                    logger.disabled = False
                except Exception:
                    pass
    except Exception:
        pass
    try:
        from prometheus_client import core as prom_core
        try:
            prom_core.REGISTRY = prom_core.CollectorRegistry()
        except Exception:
            pass
    except Exception:
        pass
