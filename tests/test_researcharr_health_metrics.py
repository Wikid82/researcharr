import pytest
from flask import Flask
import importlib
import sys

@pytest.fixture
def app_client(monkeypatch):
    # Import the app and create a test client for the metrics Flask app
    from researcharr import researcharr as researcharr_app
    metrics_app = researcharr_app.create_metrics_app()
    metrics_app.config["TESTING"] = True
    with metrics_app.test_client() as client:
        yield client

def test_health_endpoint_app(app_client):
    rv = app_client.get("/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["status"] == "ok"
    assert "db" in data and "config" in data and "threads" in data and "time" in data

def test_metrics_endpoint_increments_app(app_client):
    start = app_client.get("/metrics").get_json()["requests_total"]
    app_client.get("/health")
    after = app_client.get("/metrics").get_json()["requests_total"]
    assert after > start

def test_metrics_error_increment_app(app_client):
    before = app_client.get("/metrics").get_json()["errors_total"]
    app_client.get("/doesnotexist")
    after = app_client.get("/metrics").get_json()["errors_total"]
    assert after > before
