import os

import yaml


def test_api_updates_ignore_until(client, login):
    # login first
    login()
    rv = client.post("/api/updates/ignore", json={"mode": "until", "days": 1})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("result") == "ok"

    # persisted config should contain ignored_until
    cfg_file = os.path.join(os.getenv("CONFIG_DIR"), "updates.yml")
    assert os.path.exists(cfg_file)
    with open(cfg_file) as fh:
        cfg = yaml.safe_load(fh) or {}
    assert "ignored_until" in cfg


def test_api_updates_ignore_invalid_days(client, login):
    login()
    rv = client.post("/api/updates/ignore", json={"mode": "until", "days": 0})
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get("error") == "invalid_days"


def test_api_updates_unignore(client, login):
    login()
    # set a release-based ignore first
    rv = client.post("/api/updates/ignore", json={"mode": "release", "release_tag": "v1.2.3"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("result") == "ok"

    # now unignore
    rv2 = client.post("/api/updates/unignore", json={})
    assert rv2.status_code == 200
    data2 = rv2.get_json()
    assert data2.get("result") == "ok"

    cfg_file = os.path.join(os.getenv("CONFIG_DIR"), "updates.yml")
    if os.path.exists(cfg_file):
        with open(cfg_file) as fh:
            cfg = yaml.safe_load(fh) or {}
        # ensure ignored keys are removed
        assert "ignored_release" not in cfg
        assert "ignored_until" not in cfg


def test_api_updates_upgrade_invalid_url(client, login):
    login()
    # Ensure running-in-image detection does not short-circuit upgrade logic
    try:
        import researcharr.factory as _factory

        # Force the helper to return False for deterministic URL validation
        # If caller provided a pytest monkeypatch fixture, use it; otherwise
        # fall back to directly setting the attribute.
        try:
            # monkeypatch fixture not available here directly, so set attribute
            _factory._running_in_image = lambda: False
        except Exception:
            pass
    except Exception:
        pass

    rv = client.post("/api/updates/upgrade", json={"asset_url": "ftp://example.com/file"})
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get("error") == "invalid_asset_url"
