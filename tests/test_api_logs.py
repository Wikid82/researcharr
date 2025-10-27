import os
from pathlib import Path

import pytest


def login_client(app):
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    return client


def test_api_logs_tail_and_download(tmp_path, monkeypatch):
    # Prepare temp log file and CONFIG_DIR
    logf = tmp_path / "app.log"
    lines = [f"line {i}" for i in range(10)]
    logf.write_text("\n".join(lines) + "\n")

    monkeypatch.setenv("WEBUI_LOG", str(logf))
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # Tail last 3 lines
    r = client.get("/api/logs?lines=3")
    assert r.status_code == 200
    j = r.get_json()
    assert "content" in j
    assert "line 9" in j["content"]
    assert "line 7" in j["content"]

    # Download should return file contents
    r2 = client.get("/api/logs?download=1")
    assert r2.status_code == 200
    data = r2.data.decode("utf-8", errors="ignore")
    assert "line 0" in data
