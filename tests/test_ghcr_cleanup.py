import json
import os

SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", ".github", "scripts", "ghcr_cleanup.py"
)


def _fake_response(json_data, status_code=200):
    from types import SimpleNamespace

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

    # run the script as a module but call its main() to ensure it executes
    spec = importlib.util.spec_from_file_location("ghcr_cleanup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # monkeypatch sys.argv so argument parsing picks up our argv
    import sys

    old_argv = sys.argv[:]
    try:
        sys.argv = argv
        # call main if present
        if hasattr(module, "main"):
            module.main()
    finally:
        sys.argv = old_argv

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
        print(f"DEBUG: fake_get called with url={url}")
        # parse page param explicitly
        page = None
        if "?" in url:
            q = url.split("?", 1)[1]
            for part in q.split("&"):
                if part.startswith("page="):
                    try:
                        page = int(part.split("=", 1)[1])
                    except Exception:
                        page = None
        # return packages/versions only for page=1 or when page is None
        if "packages" in url and "versions" not in url:
            if page in (None, 1):
                return _fake_response([{"name": "researcharr", "id": 123}])
            return _fake_response([])
        if "versions" in url:
            if page in (None, 1):
                return _fake_response(versions)
            return _fake_response([])
        return _fake_response([], status_code=404)

    def fake_delete(url, headers=None):
        raise AssertionError("delete should not be called in dry-run")

    env = {
        "GHCR_PAT": "token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "365",
        "DRY_RUN": "true",
    }

    # run the script (it defaults to dry-run)
    run_script_capture(
        monkeypatch, tmp_path, fake_get, fake_delete, env=env, args=["--dry-run"]
    )

    report = tmp_path / "report.json"
    if not report.exists():
        print(f"DEBUG: Contents of {tmp_path}: {list(tmp_path.iterdir())}")
    assert report.exists(), f"report.json not found in {tmp_path}"
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
        print(f"DEBUG: fake_get called with url={url}")
        page = None
        if "?" in url:
            q = url.split("?", 1)[1]
            for part in q.split("&"):
                if part.startswith("page="):
                    try:
                        page = int(part.split("=", 1)[1])
                    except Exception:
                        page = None
        if "packages" in url and "versions" not in url:
            if page in (None, 1):
                return _fake_response([{"name": "researcharr", "id": 123}])
            return _fake_response([])
        if "versions" in url:
            if page in (None, 1):
                return _fake_response(versions)
            return _fake_response([])
        return _fake_response([], status_code=404)

    env = {
        "GHCR_PAT": "token",
        "OWNER": "Wikid82",
        "REPO": "researcharr",
        "DAYS": "90",
        "DRY_RUN": "true",
    }

    run_script_capture(monkeypatch, tmp_path, fake_get, env=env, args=["--dry-run"])
    report = tmp_path / "report.json"
    if not report.exists():
        print(f"DEBUG: Contents of {tmp_path}: {list(tmp_path.iterdir())}")
    data = json.loads(report.read_text())
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
        print(f"DEBUG: fake_get called with url={url}")
        page = None
        if "?" in url:
            q = url.split("?", 1)[1]
            for part in q.split("&"):
                if part.startswith("page="):
                    try:
                        page = int(part.split("=", 1)[1])
                    except Exception:
                        page = None
        if "packages" in url and "versions" not in url:
            if page in (None, 1):
                return _fake_response([{"name": "researcharr", "id": 123}])
            return _fake_response([])
        if "versions" in url:
            if page in (None, 1):
                return _fake_response(versions)
            return _fake_response([])
        return _fake_response([], status_code=404)

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
    report = tmp_path / "report.json"
    if not report.exists():
        print(f"DEBUG: Contents of {tmp_path}: {list(tmp_path.iterdir())}")
    data = json.loads(report.read_text())
    assert data["would_delete_count"] == 1
    assert len(data["deleted"]) == 1
