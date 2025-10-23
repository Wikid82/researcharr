import json
import os
from types import SimpleNamespace


SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "scripts", "ghcr_cleanup.py")


def load_module(tmp_path, monkeypatch, responses):
    # Prepare monkeypatched requests.get/delete
    import importlib.util

    spec = importlib.util.spec_from_file_location("ghcr_cleanup", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)

    # monkeypatch requests in the module namespace after loading
    class DummyResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or []
            self.text = text

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}: {self.text}")

    def fake_get(url, headers=None):
        # return based on a simple key match in the provided responses dict
        key = None
        if "/packages" in url and "versions" not in url:
            key = "packages"
        elif "/versions" in url:
            key = "versions"
        else:
            key = "other"
        data = responses.get(key, [])
        return DummyResponse(status_code=200, json_data=data)

    deleted = []

    def fake_delete(url, headers=None):
        # parse version id from URL
        vid = int(url.rstrip("/").split("/")[-1])
        deleted.append(vid)
        return DummyResponse(status_code=204)

    monkeypatch.setitem(os.environ, "OWNER", "Wikid82")
    monkeypatch.setitem(os.environ, "REPO", "researcharr")
    monkeypatch.setitem(os.environ, "GHCR_PAT", "fake-token")

    # load module
    spec.loader.exec_module(mod)
    # inject our fake requests funcs
    mod.requests.get = fake_get
    mod.requests.delete = fake_delete
    return mod, deleted


def test_dry_run_writes_report(tmp_path, monkeypatch):
    responses = {
        "packages": [{"name": "researcharr", "id": 1}],
        "versions": [
            {"id": 101, "created_at": "2020-01-01T00:00:00Z", "metadata": {"container": {"tags": []}}}
        ],
    }

    mod, deleted = load_module(tmp_path, monkeypatch, responses)

    out = tmp_path / "report.json"
    # call main with dry-run via args
    mod.main.__globals__["sys"].argv = ["ghcr_cleanup.py", "--days", "90", "--json-report", str(out), "--dry-run"]
    mod.main()

    assert out.exists()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["would_delete_count"] == 1
    assert deleted == []


def test_protected_tags_are_skipped(tmp_path, monkeypatch):
    responses = {
        "packages": [{"name": "researcharr", "id": 1}],
        "versions": [
            {"id": 201, "created_at": "2020-01-01T00:00:00Z", "metadata": {"container": {"tags": ["main"]}}}
        ],
    }

    mod, deleted = load_module(tmp_path, monkeypatch, responses)
    out = tmp_path / "report2.json"
    mod.main.__globals__["sys"].argv = ["ghcr_cleanup.py", "--days", "90", "--json-report", str(out), "--dry-run"]
    mod.main()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["would_delete_count"] == 0
    candidates = report["candidates"]
    assert candidates[0]["decision"] == "SKIP_PROTECTED"
    assert deleted == []


def test_deletion_calls_delete_endpoint(tmp_path, monkeypatch):
    responses = {
        "packages": [{"name": "researcharr", "id": 1}],
        "versions": [
            {"id": 301, "created_at": "2020-01-01T00:00:00Z", "metadata": {"container": {"tags": []}}},
            {"id": 302, "created_at": "2025-01-01T00:00:00Z", "metadata": {"container": {"tags": []}}},
        ],
    }

    mod, deleted = load_module(tmp_path, monkeypatch, responses)
    out = tmp_path / "report3.json"
    # run with no-dry-run to perform deletions
    mod.main.__globals__["sys"].argv = ["ghcr_cleanup.py", "--days", "365", "--json-report", str(out), "--no-dry-run"]
    mod.main()
    report = json.loads(out.read_text(encoding="utf-8"))
    # only the old 301 should have been deleted
    assert 301 in report["deleted"]
    assert 302 not in report["deleted"]
    assert deleted == [301]
