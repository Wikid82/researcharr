import logging


def test_logging_service_setup_logger_creates_handler(tmp_path):
    from researcharr.core.services import LoggingService

    log_file = tmp_path / "app.log"
    svc = LoggingService()
    logger = svc.setup_logger("svc.logger", str(log_file))
    assert isinstance(logger, logging.Logger)
    # Calling again should reuse same logger
    logger2 = svc.setup_logger("svc.logger", str(log_file))
    assert logger is logger2


def test_database_service_init_and_check_connection(tmp_path):
    from researcharr.core.services import DatabaseService

    db_path = tmp_path / "test.db"
    svc = DatabaseService(str(db_path))
    svc.init_db()  # creates tables and publishes event
    assert svc.check_connection() is True


def test_connectivity_service_has_valid_url_and_key():
    from researcharr.core.services import ConnectivityService

    svc = ConnectivityService()
    ok = svc.has_valid_url_and_key([
        {"enabled": True, "url": "http://example", "api_key": "k"},
        {"enabled": False},
    ])
    assert ok is True
    bad = svc.has_valid_url_and_key([
        {"enabled": True, "url": "ftp://bad", "api_key": ""},
    ])
    assert bad is False


def _fake_requests(status_code=200, raise_exc=False):
    class R:
        def __init__(self, status):
            self.status_code = status
    class Req:
        def get(self, *a, **kw):
            if raise_exc:
                raise RuntimeError("boom")
            return R(status_code)
    return Req()


def test_connectivity_service_radarr_success(monkeypatch):
    from researcharr.core.services import ConnectivityService
    svc = ConnectivityService()
    svc.requests = _fake_requests(200)
    logger = logging.getLogger("svc.test")
    assert svc.check_radarr_connection("http://ok", "k", logger) is True


def test_connectivity_service_radarr_failure_and_exception(monkeypatch):
    from researcharr.core.services import ConnectivityService

    logger = logging.getLogger("svc.test2")
    svc = ConnectivityService()
    svc.requests = _fake_requests(404)
    assert svc.check_radarr_connection("http://bad", "k", logger) is False
    svc = ConnectivityService()
    svc.requests = _fake_requests(raise_exc=True)
    assert svc.check_radarr_connection("http://err", "k", logger) is False


def test_connectivity_service_sonarr_success_and_failure(monkeypatch):
    from researcharr.core.services import ConnectivityService

    logger = logging.getLogger("svc.test3")
    svc = ConnectivityService()
    svc.requests = _fake_requests(200)
    assert svc.check_sonarr_connection("http://ok", "k", logger) is True
    svc = ConnectivityService()
    svc.requests = _fake_requests(404)
    assert svc.check_sonarr_connection("http://bad", "k", logger) is False


def test_metrics_service_counters_and_get():
    from researcharr.core.services import MetricsService

    m = MetricsService()
    m.increment_requests()
    m.increment_errors()
    m.record_service_metric("svc", "latency_ms", 5)
    data = m.get_metrics()
    assert data["requests_total"] >= 1
    assert data["errors_total"] >= 1
    assert data["services"]["svc"]["latency_ms"] == 5


def test_health_service_with_stubs(monkeypatch):
    from researcharr.core import services
    from researcharr.core.services import HealthService

    class _DB:
        db_path = "db"
        def check_connection(self):
            return True
    class _ConfigMgr:
        validation_errors = []
    class _Container:
        def resolve(self, name):
            if name == "database_service":
                return _DB()
            raise KeyError(name)

    # Monkeypatch container and config manager
    monkeypatch.setattr(services, "get_container", lambda: _Container())
    monkeypatch.setattr(services, "get_config_manager", lambda: _ConfigMgr())

    hs = HealthService()
    status = hs.check_system_health()
    assert status["status"] in {"ok", "warning", "error"}
    assert "database" in status["components"]


def test_metrics_app_error_handler_and_events():
    from researcharr.core.services import create_metrics_app

    app = create_metrics_app()
    with app.test_client() as c:  # type: ignore[attr-defined]
        r = c.get("/no-such-route")
        assert r.status_code == 500


def test_health_service_config_error_branch(monkeypatch):
    from researcharr.core import services
    from researcharr.core.services import HealthService

    class _DB:
        db_path = "db"
        def check_connection(self):
            return True
    class _Container:
        def resolve(self, name):
            if name == "database_service":
                return _DB()
            raise KeyError(name)

    monkeypatch.setattr(services, "get_container", lambda: _Container())
    monkeypatch.setattr(services, "get_config_manager", lambda: (_ for _ in ()).throw(RuntimeError("cfg err")))

    hs = HealthService()
    status = hs.check_system_health()
    assert status["components"]["configuration"]["status"] == "error"
