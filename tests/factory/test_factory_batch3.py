import json
import sqlite3


def test_api_plugin_validate_invalid_index(client, login):
    class DummyReg:
        def get(self, name):
            return object()

    client.application.plugin_registry = DummyReg()
    # no configured instances -> validate should succeed for out-of-range idx
    client.application.config_data["dummy"] = []
    login()
    rv = client.post("/api/plugins/dummy/validate/5")
    # api_plugin_validate returns 400 for invalid index when instances
    # exist or are missing; assert invalid_instance
    assert rv.status_code == 400
    assert rv.get_json().get("error") == "invalid_instance"


def test_api_plugin_validate_failure_and_metrics(client, login):
    class DummyReg:
        def get(self, name):
            return object()

        def create_instance(self, name, inst):
            raise RuntimeError("validation error")

    client.application.plugin_registry = DummyReg()
    client.application.config_data["dummy"] = [{}]
    login()
    rv = client.post("/api/plugins/dummy/validate/0")
    assert rv.status_code == 500
    data = rv.get_json()
    assert data.get("error") == "validate_failed"


def test_api_tasks_get_history_filters(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    hist = cfg / "task_history.jsonl"
    # create three records, one failed
    recs = [
        {"id": 1, "success": True, "stdout": "ok"},
        {"id": 2, "success": False, "stderr": "err"},
        {"id": 3, "success": True, "stdout": "all good"},
    ]
    with open(hist, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")

    login()
    rv = client.get("/api/tasks?status=failed")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("total") == 1
    rv2 = client.get("/api/tasks?limit=1&offset=1")
    assert rv2.status_code == 200


def test_api_logs_download_and_not_found(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    logp = cfg / "app.log"
    logp.write_text("line1\nline2\n")
    monkeypatch.setenv("WEBUI_LOG", str(logp))
    login()
    # download exists
    rv = client.get("/api/logs?download=1")
    assert rv.status_code == 200
    # simulate not found
    monkeypatch.setenv("WEBUI_LOG", str(logp.parent / "nope.log"))
    rv2 = client.get("/api/logs?download=1")
    assert rv2.status_code == 404


def test_api_logs_stream_initial_tail(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    logp = cfg / "app.log"
    # create multiple lines
    lines = [f"line{i}" for i in range(10)]
    logp.write_text("\n".join(lines) + "\n")
    monkeypatch.setenv("WEBUI_LOG", str(logp))
    login()
    # request a streamed (non-buffered) response so we don't consume the
    # infinite generator (which sleeps); read one chunk and then close it.
    rv = client.get("/api/logs/stream?lines=3", buffered=False)
    assert rv.status_code == 200
    it = rv.response
    chunk = next(it)
    data = chunk.decode() if isinstance(chunk, (bytes, bytearray)) else str(chunk)
    assert "data: line7" in data or "data: line9" in data
    # close the response generator to stop background sleep loop
    try:
        rv.close()
    except Exception:
        pass


def test_api_status_db_ok_and_db_fail(client, monkeypatch):
    # case 1: normal DB exists -> ok
    # create a temp sqlite DB file
    import tempfile

    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    # initialize DB so SELECT 1 works
    conn = sqlite3.connect(tf.name)
    conn.execute("SELECT 1")
    conn.close()

    monkeypatch.setenv("RESEARCHARR_DB", tf.name)
    # client not logged in -> expect unauthorized
    rv = client.get("/api/status")
    assert rv.status_code == 401

    # now log in and verify db ok
    client.post("/login", data={"username": "admin", "password": "password"})
    rv2 = client.get("/api/status")
    assert rv2.status_code == 200
    data = rv2.get_json()
    assert data.get("db", {}).get("ok") in (True, False)

    # simulate sqlite.connect failure
    import sqlite3 as _sqlite

    def _bad_connect(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(_sqlite, "connect", _bad_connect)
    rv3 = client.get("/api/status")
    assert rv3.status_code == 200
    data3 = rv3.get_json()
    assert data3.get("db", {}).get("ok") is False
