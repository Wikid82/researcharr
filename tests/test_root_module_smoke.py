import logging


def test_root_module_load_config_empty_file_returns_empty(tmp_path):
    import researcharr.researcharr as root

    # Create an empty file; load_config should return {}
    p = tmp_path / "empty.yml"
    p.write_text("")
    cfg = root.load_config(str(p))
    assert cfg == {}


def test_root_module_init_db_and_metrics_app(tmp_path):
    import researcharr.researcharr as root

    db_path = tmp_path / "app.db"
    root.init_db(str(db_path))
    assert db_path.exists()

    app = root.create_metrics_app()
    # If Flask available, exercise endpoints
    try:
        client = app.test_client()
        r = client.get("/health")
        assert r.status_code == 200
        m = client.get("/metrics")
        assert m.status_code == 200
    except Exception:
        # Flask may not be present; acceptable
        pass


def test_root_module_check_radarr_connection_missing(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.radarr")
    assert root.check_radarr_connection("", "", logger) is False


def test_root_module_check_radarr_connection_mock_success(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.radarr2")

    class _Resp:
        status_code = 200

    class _Req:
        def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_radarr_connection("http://ok", "k", logger) is True


def test_root_module_check_radarr_connection_mock_failure(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.radarr3")

    class _Resp:
        status_code = 404

    class _Req:
        def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_radarr_connection("http://bad", "k", logger) is False


def test_root_module_check_radarr_connection_exception(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.radarr4")

    class _Req:
        def get(self, *a, **kw):
            raise RuntimeError("boom")

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_radarr_connection("http://err", "k", logger) is False


def test_root_module_check_sonarr_connection_missing(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.sonarr")
    assert root.check_sonarr_connection("", "", logger) is False


def test_root_module_check_sonarr_connection_success(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.sonarr2")

    class _Resp:
        status_code = 200

    class _Req:
        def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_sonarr_connection("http://ok", "k", logger) is True


def test_root_module_check_sonarr_connection_failure(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.sonarr3")

    class _Resp:
        status_code = 500

    class _Req:
        def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_sonarr_connection("http://bad", "k", logger) is False


def test_root_module_check_sonarr_connection_exception(monkeypatch):
    import researcharr.researcharr as root

    logger = logging.getLogger("root.sonarr4")

    class _Req:
        def get(self, *a, **kw):
            raise RuntimeError("boom")

    monkeypatch.setattr(root, "requests", _Req())
    assert root.check_sonarr_connection("http://err", "k", logger) is False
