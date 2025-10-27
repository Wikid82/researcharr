import os

import yaml


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_plugin_instances_add_update_delete_and_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # mock a minimal registry so plugin is considered known
    class DummyRegistry:
        def __init__(self):
            pass

        def get(self, name):
            return object

    app.plugin_registry = DummyRegistry()

    plugin_name = "example"

    # attempt to add invalid instance (enabled but missing url/api_key)
    r = client.post(
        f"/api/plugins/{plugin_name}/instances",
        json={"action": "add", "instance": {"enabled": True}},
    )
    assert r.status_code == 400
    assert r.get_json().get("error") == "invalid_instance"

    # add valid instance
    inst = {"enabled": True, "url": "http://example.local", "api_key": "secret"}
    r2 = client.post(
        f"/api/plugins/{plugin_name}/instances",
        json={"action": "add", "instance": inst},
    )
    assert r2.status_code == 200
    assert r2.get_json().get("result") == "ok"

    # persisted file should exist under CONFIG_DIR/plugins/example.yml
    p = tmp_path / "plugins" / f"{plugin_name}.yml"
    assert p.exists()
    persisted = yaml.safe_load(p.read_text())
    assert isinstance(persisted, list)
    assert persisted[0].get("url") == inst["url"]

    # update the instance
    new_inst = {"enabled": True, "url": "http://new.example", "api_key": "newkey"}
    r3 = client.post(
        f"/api/plugins/{plugin_name}/instances",
        json={"action": "update", "idx": 0, "instance": new_inst},
    )
    assert r3.status_code == 200
    assert r3.get_json().get("result") == "ok"
    persisted2 = yaml.safe_load(p.read_text())
    assert persisted2[0].get("url") == new_inst["url"]

    # delete the instance
    r4 = client.post(
        f"/api/plugins/{plugin_name}/instances", json={"action": "delete", "idx": 0}
    )
    assert r4.status_code == 200
    assert r4.get_json().get("result") == "ok"
    persisted3 = yaml.safe_load(p.read_text())
    assert persisted3 == []
