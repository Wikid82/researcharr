def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_backups_create_list_download_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # Create a backup
    r = client.post("/api/backups/create")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("result") == "ok"
    name = j.get("name")
    assert name

    # List backups
    r2 = client.get("/api/backups")
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert "backups" in j2

    # Download backup
    r3 = client.get(f"/api/backups/download/{name}")
    assert r3.status_code == 200
    # ensure it's a gzipped tar by checking gzip magic bytes
    assert r3.data[:2] == b"\x1f\x8b"

    # Delete backup
    r4 = client.delete(f"/api/backups/delete/{name}")
    assert r4.status_code == 200
    j4 = r4.get_json()
    assert j4.get("result") == "deleted"
