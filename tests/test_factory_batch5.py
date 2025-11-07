def test_backups_download_and_delete_variants(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    backups = cfg / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    login()

    # path traversal attempt -> invalid_name
    rv = client.get("/api/backups/download/../etc/passwd")
    assert rv.status_code == 400

    # not found
    rv2 = client.get("/api/backups/download/missing.zip")
    assert rv2.status_code == 404

    # create a real file and download/delete
    f = backups / "real.zip"
    f.write_text("content")
    rv3 = client.get("/api/backups/download/real.zip")
    assert rv3.status_code == 200

    # delete existing
    rv4 = client.delete("/api/backups/delete/real.zip")
    assert rv4.status_code == 200
    j = rv4.get_json()
    assert j.get("result") == "deleted"

    # delete missing
    rv5 = client.delete("/api/backups/delete/nope.zip")
    assert rv5.status_code == 404


def test_updates_upgrade_in_image_and_invalid_url(client, login, monkeypatch):
    # when running in image, upgrade is disallowed
    monkeypatch.setenv("CONTAINER", "1")
    login()
    rv = client.post("/api/updates/upgrade", json={"asset_url": "https://example.com/asset.zip"})
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get("error") == "in_image_runtime"

    # invalid asset URL
    monkeypatch.delenv("CONTAINER", raising=False)
    rv2 = client.post("/api/updates/upgrade", json={"asset_url": "ftp://bad"})
    assert rv2.status_code == 400
    d2 = rv2.get_json()
    assert d2.get("error") == "invalid_asset_url"
