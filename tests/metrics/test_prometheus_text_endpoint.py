
import pytest

pytest.importorskip("prometheus_client")


def test_metrics_prometheus_text_default_registry(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "1")
    from researcharr.core.services import create_metrics_app

    app = create_metrics_app()
    # touch cache to create counters
    from researcharr import cache

    cache.get("missing:key")
    cache.set("a", 1, ttl=5)
    cache.get("a")
    cache.invalidate("a")

    with app.test_client() as c:
        r = c.get("/metrics.prom")
        assert r.status_code == 200
        body = r.data.decode()
        # Expect Prometheus exposition format present
        assert "# HELP" in body and "# TYPE" in body


def test_api_metrics_prometheus_text(monkeypatch):
    monkeypatch.setenv("RESEARCHARR_PROMETHEUS_CACHE", "1")
    # Import factory create_app if present to build full app
    from researcharr.factory import create_app  # type: ignore

    app = create_app()
    with app.test_client() as c:
        r = c.get("/api/v1/metrics.prom")
        # If prometheus_client unavailable, endpoint returns 501; we skip earlier so expect 200
        assert r.status_code == 200
        body = r.data.decode()
        assert "# HELP" in body and "# TYPE" in body
