from researcharr.researcharr import (
    create_metrics_app,
    setup_logger,
    check_radarr_connection,
    check_sonarr_connection,
)


def test_metrics_app_health_and_metrics(tmp_path):
    app = create_metrics_app()
    client = app.test_client()

    # First request should increment requests_total
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"

    m = client.get("/metrics")
    assert m.status_code == 200
    metrics = m.get_json()
    assert "requests_total" in metrics


def test_metrics_app_error_handler_increments_errors(tmp_path):
    app = create_metrics_app()
    client = app.test_client()

    # Trigger a 404 which our handler maps to a 500 response and increments
    r = client.get("/nonexistent")
    assert r.status_code == 500
    data = r.get_json()
    assert data == {"error": "internal error"}
    # After the error, metrics endpoint should show at least one error
    metrics = client.get("/metrics").get_json()
    assert metrics["errors_total"] >= 1


def test_setup_logger_level(tmp_path):
    log_file = tmp_path / "l.log"
    logger = setup_logger("logger_test", str(log_file), level=10)
    assert logger.level == 10


def test_check_connections_success(tmp_path, monkeypatch):
    class R:
        status_code = 200

    monkeypatch.setattr("researcharr.researcharr.requests.get", lambda url: R())
    logger = setup_logger("ok_logger", str(tmp_path / "ok.log"))
    assert check_radarr_connection("http://x", "k", logger) is True
    assert check_sonarr_connection("http://x", "k", logger) is True
