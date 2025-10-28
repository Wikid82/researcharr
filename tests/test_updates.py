import requests
import yaml


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_api_updates_fetch_success(tmp_path, monkeypatch):
    # ensure CONFIG_DIR isolation
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    # prepare a fake release JSON
    release = {
        "tag_name": "v1.2.3",
        "name": "release-name",
        "body": "notes",
        "published_at": "2020-01-01T00:00:00Z",
        "html_url": "https://example.com/release",
        "assets": [
            {
                "name": "asset.tar.gz",
                "browser_download_url": "https://example.com/asset.tar.gz",
            }
        ],
    }

    class MockJSONResp:
        def raise_for_status(self):
            return None

        def json(self):
            return release

    # requests.get should return a JSON response for non-stream calls
    def fake_get(*args, **kwargs):
        # if stream kw present, behave differently in other tests
        if kwargs.get("stream"):
            raise RuntimeError("unexpected stream in this test")
        return MockJSONResp()

    monkeypatch.setenv("UPDATE_CHECK_URL", "https://api.example.com/releases/latest")
    monkeypatch.setattr("requests.get", fake_get)

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    r = client.get("/api/updates")
    assert r.status_code == 200
    j = r.get_json()
    assert j["latest"]["tag_name"] == "v1.2.3"
    # cache should be persisted
    cache_file = tmp_path / "updates_cache.yml"
    assert cache_file.exists()
    data = yaml.safe_load(cache_file.read_text())
    assert data.get("latest", {}).get("tag_name") == "v1.2.3"


def test_api_updates_fetch_failure_backoff(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    # simulate network error
    def fake_get_err(*args, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr("requests.get", fake_get_err)
    # set small base backoff for deterministic behavior
    monkeypatch.setenv("UPDATE_BACKOFF_BASE", "1")
    monkeypatch.setenv("UPDATE_BACKOFF_CAP", "10")

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    r = client.get("/api/updates")
    assert r.status_code == 200
    j = r.get_json()
    # after failure, cache metadata should include failed_attempts and next_try
    cache = j.get("cache") or {}
    assert cache.get("failed_attempts", 0) >= 1
    assert cache.get("next_try") is not None


def test_updates_ignore_and_unignore(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # ignore a specific release
    r = client.post(
        "/api/updates/ignore", json={"mode": "release", "release_tag": "v9"}
    )
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("result") == "ok"
    cfg_file = tmp_path / "updates.yml"
    assert cfg_file.exists()
    cfg = yaml.safe_load(cfg_file.read_text())
    assert cfg.get("ignored_release") == "v9"

    # unignore
    r2 = client.post("/api/updates/unignore")
    assert r2.status_code == 200
    cfg2 = yaml.safe_load(cfg_file.read_text())
    assert not cfg2.get("ignored_release")


def test_api_updates_upgrade_starts_download(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    # provide a fake streaming response for download
    class MockStreamResp:
        def __init__(self, content=b"hello"):
            self._content = content

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield self._content

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_get(url, *args, **kwargs):
        # download call uses stream=True
        if kwargs.get("stream"):
            return MockStreamResp(b"dummydata")

        # other calls (release fetch) can return minimal JSON
        class J:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "tag_name": "vX",
                    "assets": [{"name": "a", "browser_download_url": url}],
                }

        return J()

    monkeypatch.setattr("requests.get", fake_get)

    # Make threading run synchronously so we can observe the written file

    class SyncThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self._target = target
            self._args = args or ()

        def start(self):
            # run synchronously
            if self._target:
                self._target(*self._args)

    monkeypatch.setattr("threading.Thread", SyncThread)

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    asset_url = "https://example.com/somefile.bin"
    r = client.post("/api/updates/upgrade", json={"asset_url": asset_url})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("result") == "started"

    # check downloads directory
    dl_dir = tmp_path / "updates" / "downloads"
    assert dl_dir.exists()
    # find any file in downloads
    files = list(dl_dir.iterdir())
    assert files, "no downloaded file written"
