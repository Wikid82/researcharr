import json


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def make_entry(j):
    return json.dumps(j)


def test_api_tasks_filters_and_pagination(tmp_path, monkeypatch):
    hist = tmp_path / "task_history.jsonl"
    # create several records: some success, some failed, some with stderr
    records = [
        {"id": 1, "stdout": "ok1", "stderr": "", "success": True, "start_ts": 100},
        {
            "id": 2,
            "stdout": "err2",
            "stderr": "boom",
            "success": False,
            "start_ts": 200,
        },
        {"id": 3, "stdout": "ok3", "stderr": "", "success": True, "start_ts": 300},
        {"id": 4, "stdout": "searchme", "stderr": "", "success": True, "start_ts": 400},
    ]
    # write JSON lines (newest last)
    with open(hist, "w") as fh:
        for r in records:
            fh.write(make_entry(r) + "\n")

    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # no filters -> total should be 4
    r = client.get("/api/tasks")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("total") == 4

    # filter failed -> should return only one
    r2 = client.get("/api/tasks?status=failed")
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert j2.get("total") == 1
    assert j2.get("runs")[0]["id"] == 2

    # search text -> match record with stdout 'searchme'
    r3 = client.get("/api/tasks?search=searchme")
    j3 = r3.get_json()
    assert j3.get("total") == 1
    assert j3.get("runs")[0]["id"] == 4

    # pagination: limit 2 offset 0 -> two newest
    r4 = client.get("/api/tasks?limit=2&offset=0")
    j4 = r4.get_json()
    assert len(j4.get("runs")) == 2
