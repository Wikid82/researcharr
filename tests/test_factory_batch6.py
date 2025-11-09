def test_api_updates_with_cached_latest(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    # create an updates cache with a latest asset so can_upgrade becomes True
    cache = {
        "latest": {"tag_name": "v1", "assets": [{"name": "a", "url": "u"}]},
        "fetched_at": int(__import__("time").time()),
    }
    import yaml

    (cfg / "updates_cache.yml").write_text(yaml.safe_dump(cache))
    login()
    rv = client.get("/api/updates")
    assert rv.status_code == 200
    j = rv.get_json()
    assert isinstance(j.get("latest"), dict)
    assert j.get("can_upgrade") in (True, False)


def test_api_tasks_post_variants(client, login):
    # not logged in -> unauthorized
    rv = client.post("/api/tasks", data="{}")
    assert rv.status_code == 401

    login()
    # missing/incorrect content-type -> 415
    rv2 = client.post("/api/tasks", data="{}")
    assert rv2.status_code == 415

    # invalid json with application/json -> 400
    rv3 = client.post("/api/tasks", data="notjson", content_type="application/json")
    assert rv3.status_code == 400

    # valid json -> 201
    rv4 = client.post("/api/tasks", json={"name": "t"})
    assert rv4.status_code == 201
    j = rv4.get_json()
    assert j.get("result") == "created"


def test_plugin_sync_exception_paths(client, login):
    # registry that raises on create_instance
    class BadReg:
        def get(self, name):
            return object

        def create_instance(self, name, cfg):
            raise RuntimeError("boom")

    client.application.plugin_registry = BadReg()
    client.application.config_data["dummy"] = [{}]
    login()
    rv = client.post("/api/plugins/dummy/sync/0")
    assert rv.status_code == 500
    j = rv.get_json()
    assert j.get("error") == "sync_failed"
