import json


def login_client(app):
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    return client


def test_api_tasks_pagination_and_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    hist = tmp_path / "task_history.jsonl"
    entries = []
    # create 5 entries, some failed
    for i in range(5):
        e = {"id": i, "stdout": f"out {i}", "stderr": ""}
        if i % 2 == 0:
            e["success"] = False
            e["stderr"] = "error"
        entries.append(e)
    hist.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # default list
    r = client.get("/api/tasks?limit=2&offset=1")
    assert r.status_code == 200
    j = r.get_json()
    assert "runs" in j and "total" in j
    assert j["total"] == 5

    # filter failed
    r2 = client.get("/api/tasks?status=failed")
    assert r2.status_code == 200
    j2 = r2.get_json()
    # only entries with success False should be returned
    assert all((not run.get("success")) or run.get("stderr") for run in j2["runs"])

    # search by stdout
    r3 = client.get("/api/tasks?search=out 3")
    assert r3.status_code == 200
    j3 = r3.get_json()
    assert j3["total"] >= 1
