import os
import time

import yaml


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_updates_skips_fetch_when_cache_fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    cache_file = tmp_path / "updates_cache.yml"
    now = int(time.time())
    cache_file.write_text(
        yaml.safe_dump({"fetched_at": now, "latest": {"tag_name": "v1"}})
    )

    # make requests.get raise if called (should not be called because cache is fresh)
    def fail_get(*a, **k):
        raise RuntimeError("requests.get should not be called when cache fresh")

    import requests

    monkeypatch.setattr("requests.get", fail_get)

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    r = client.get("/api/updates")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("latest", {}).get("tag_name") == "v1"


def test_updates_upgrade_in_image_guard(monkeypatch):
    # set IN_CONTAINER env so _running_in_image returns True
    monkeypatch.setenv("IN_CONTAINER", "1")
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    r = client.post("/api/updates/upgrade", json={"asset_url": "https://example.com/a"})
    assert r.status_code == 400
    j = r.get_json()
    assert j.get("error") == "in_image_runtime"
