import json
import os
from types import SimpleNamespace

SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", ".github", "scripts", "ghcr_cleanup.py"
)


def _fake_response(json_data, status_code=200):
    r = SimpleNamespace()
    r.status_code = status_code

    def json_func():
        return json_data

    r.json = json_func

    r.text = json.dumps(json_data)

    def raise_for_status():
        if r.status_code >= 400:
            raise Exception(f"HTTP {r.status_code}: {r.text}")

    r.raise_for_status = raise_for_status
    return r


def run_script_capture(
    monkeypatch, tmp_path, requests_get, requests_delete=None, env=None, args=None
):
    # monkeypatch requests.get and requests.delete
    import importlib.util
    import runpy

    if requests_get is not None:
        monkeypatch.setattr("requests.get", requests_get)
    if requests_delete is not None:
        monkeypatch.setattr("requests.delete", requests_delete)

    env = env or {}
    old_env = os.environ.copy()
    os.environ.update(env)

    report_path = tmp_path / "report.json"
    argv = ["ghcr_cleanup.py"]
    if args:
        argv.extend(args)
    argv.extend(["--json-report", str(report_path)])

    # run the script as a module by exec file for __main__ behavior
    spec = importlib.util.spec_from_file_location("ghcr_cleanup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # restore env
    os.environ.clear()
    os.environ.update(old_env)

    # return the report path for inspection
    return report_path


def test_dry_run_writes_report(monkeypatch, tmp_path):
    # One old version without protected tags
    versions = [
        {
            "id": 1,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": ["feature-x"]}},
        }
    ]

    def fake_get(url, headers=None):
        if "packages" in url and "versions" not in url:
            return _fake_response([{"name": "researcharr", "id": 123}])
        return _fake_response(versions)

    def fake_delete(url, headers=None):
        raise AssertionError("delete should not be called in dry-run")

    env = {
        "GHCR_PAT": "token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "90",
        "DRY_RUN": "true",
    }

    # run the script (it defaults to dry-run)
    run_script_capture(
        monkeypatch, tmp_path, fake_get, fake_delete, env=env, args=["--dry-run"]
    )

    report = tmp_path / "report.json"
    assert report.exists()
    data = json.loads(report.read_text())
    assert data["scanned"] == 1
    assert data["would_delete_count"] == 1


def test_protected_tag_skipped(monkeypatch, tmp_path):
    # Version has protected tag 'main'
    versions = [
        {
            "id": 2,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": ["main"]}},
        }
    ]

    def fake_get(url, headers=None):
        if "packages" in url and "versions" not in url:
            return _fake_response([{"name": "researcharr", "id": 123}])
        return _fake_response(versions)

    env = {
        "GHCR_PAT": "token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "90",
        "DRY_RUN": "true",
    }

    run_script_capture(monkeypatch, tmp_path, fake_get, env=env, args=["--dry-run"])
    data = json.loads((tmp_path / "report.json").read_text())
    assert data["scanned"] == 1
    assert data["would_delete_count"] == 0
    cand = data["candidates"][0]
    assert cand["decision"] == "SKIP_PROTECTED"


def test_deletion_calls_delete_endpoint(monkeypatch, tmp_path):
    # One deletable version and one protected
    versions = [
        {
            "id": 3,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": ["old"]}},
        },
        {
            "id": 4,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": ["development"]}},
        },
    ]

    def fake_get(url, headers=None):
        if "packages" in url and "versions" not in url:
            return _fake_response([{"name": "researcharr", "id": 123}])
        return _fake_response(versions)

    deleted = []

    def fake_delete(url, headers=None):
        deleted.append(url)
        return _fake_response({}, status_code=204)

    env = {
        "GHCR_PAT": "token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "90",
        "DRY_RUN": "false",
    }

    run_script_capture(
        monkeypatch, tmp_path, fake_get, fake_delete, env=env, args=["--no-dry-run"]
    )

    data = json.loads((tmp_path / "report.json").read_text())
    assert data["would_delete_count"] == 1
    assert len(data["deleted"]) == 1


import json
import os
import types

import pytest

SCRIPT = "researcharr/.github/scripts/ghcr_cleanup.py"


def make_response(json_obj, status_code=200):
    class R:
        def __init__(self, j, status):
            self._j = j
            self.status_code = status

        def json(self):
            return self._j

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

        @property
        def text(self):
            return str(self._j)

    return R(json_obj, status_code)


def run_script(tmp_path, monkeypatch, env=None, args=None):
    # prepare env and argv
    env = env or {}
    old_env = os.environ.copy()
    os.environ.update(env)
    argv = [SCRIPT]
    if args:
        argv.extend(args)
    monkeypatch.setattr("sys.argv", argv)
    # import as module
    spec = types.ModuleType("ghcr_cleanup")
    spec.__dict__["__name__"] = "__main__"
    with open(SCRIPT, "r", encoding="utf-8") as fh:
        code = fh.read()
    exec(compile(code, "ghcr_cleanup.py", "exec"), spec.__dict__)
    # restore env
    os.environ.clear()
    os.environ.update(old_env)
    return spec


def test_dry_run_writes_report(tmp_path, monkeypatch):
    # Mock packages list (one package matching repo)
    packages = [{"name": "researcharr", "id": 1}]

    # create versions: one old (to delete), one new (keep)
    old_date = "2020-01-01T00:00:00Z"
    new_date = "2100-01-01T00:00:00Z"
    versions = [
        {"id": 101, "created_at": old_date, "metadata": {"container": {"tags": []}}},
        {"id": 102, "created_at": new_date, "metadata": {"container": {"tags": []}}},
    ]

    calls = {"get": []}

    def fake_get(url, headers=None):
        calls["get"].append(url)
        if "packages" in url and "versions" not in url:
            return make_response(packages)
        if "versions" in url:
            return make_response(versions)
        return make_response([], 404)

    monkeypatch.setattr("requests.get", fake_get)

    report_path = tmp_path / "report.json"

    env = {
        "GHCR_PAT": "fake-token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "365",
        "JSON_REPORT": str(report_path),
        "DRY_RUN": "true",
    }

    spec = run_script(
        tmp_path,
        monkeypatch,
        env=env,
        args=["--json-report", str(report_path), "--days", "365", "--dry-run"],
    )

    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["package"] == "researcharr"
    # candidate with id 101 should be marked DELETE
    ids = {c["version_id"]: c for c in data["candidates"]}
    assert ids[101]["decision"] == "DELETE"
    assert ids[102]["decision"] == "KEEP"


def test_protected_tag_skipped(tmp_path, monkeypatch):
    packages = [{"name": "researcharr", "id": 1}]
    versions = [
        {
            "id": 201,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": ["main"]}},
        },
    ]

    def fake_get(url, headers=None):
        if "packages" in url and "versions" not in url:
            return make_response(packages)
        if "versions" in url:
            return make_response(versions)
        return make_response([], 404)

    monkeypatch.setattr("requests.get", fake_get)

    report_path = tmp_path / "report2.json"
    env = {
        "GHCR_PAT": "fake",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "JSON_REPORT": str(report_path),
        "DRY_RUN": "true",
    }
    spec = run_script(
        tmp_path,
        monkeypatch,
        env=env,
        args=["--json-report", str(report_path), "--dry-run"],
    )

    data = json.loads(report_path.read_text(encoding="utf-8"))
    ids = {c["version_id"]: c for c in data["candidates"]}
    assert ids[201]["decision"] == "SKIP_PROTECTED"


def test_deletion_calls_delete_endpoint(tmp_path, monkeypatch):
    packages = [{"name": "researcharr", "id": 1}]
    versions = [
        {
            "id": 301,
            "created_at": "2000-01-01T00:00:00Z",
            "metadata": {"container": {"tags": []}},
        },
    ]

    def fake_get(url, headers=None):
        if "packages" in url and "versions" not in url:
            return make_response(packages)
        if "versions" in url:
            return make_response(versions)
        return make_response([], 404)

    deleted = {"called_with": []}

    def fake_delete(url, headers=None):
        deleted["called_with"].append(url)
        return make_response({}, 204)

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.delete", fake_delete)

    report_path = tmp_path / "report3.json"
    env = {
        "GHCR_PAT": "fake",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "JSON_REPORT": str(report_path),
        "DRY_RUN": "false",
    }
    spec = run_script(
        tmp_path,
        monkeypatch,
        env=env,
        args=["--json-report", str(report_path), "--no-dry-run"],
    )

    # ensure delete was called
    assert len(deleted["called_with"]) >= 1
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert 301 in data.get("deleted", [])
