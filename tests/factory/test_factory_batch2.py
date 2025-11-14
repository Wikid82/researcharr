import io


def test_api_plugins_requires_login(client):
    rv = client.get("/api/plugins")
    assert rv.status_code == 401


def test_api_plugins_returns_plugins_when_registry_set(client, login):
    class DummyPlugin:
        category = "media"
        description = "desc"
        docs_url = None

    class DummyReg:
        def __init__(self):
            self._map = {"dummy": DummyPlugin}

        def list_plugins(self):
            return list(self._map.keys())

        def get(self, name):
            return self._map.get(name)

        def create_instance(self, name, inst):
            class Inst:
                def validate(self):
                    return True

                def sync(self):
                    return True

                def blueprint(self):
                    return None

            return Inst()

    # install registry and configured instances
    client.application.plugin_registry = DummyReg()
    client.application.config_data["dummy"] = []
    login()
    rv = client.get("/api/plugins")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data.get("plugins"), list)


def test_api_plugin_instances_add_and_validate(client, login, monkeypatch):
    class DummyPlugin:
        pass

    class DummyReg:
        def __init__(self):
            self._map = {"dummy": DummyPlugin}

        def list_plugins(self):
            return ["dummy"]

        def get(self, name):
            return DummyPlugin

        def create_instance(self, name, inst):
            class Inst:
                def validate(self):
                    return True

                def sync(self):
                    return True

            return Inst()

    client.application.plugin_registry = DummyReg()
    client.application.config_data["dummy"] = []
    login()
    rv = client.post(
        "/api/plugins/dummy/instances",
        json={"action": "add", "instance": {"enabled": True, "url": "http://x", "api_key": "k"}},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("result") == "ok"


def test_api_plugin_instances_add_validation_failure(client, login):
    # missing api_key with enabled True -> invalid
    class DummyReg:
        def get(self, name):
            return object()

        def list_plugins(self):
            return ["dummy"]

    client.application.plugin_registry = DummyReg()
    client.application.config_data["dummy"] = []
    login()
    rv = client.post(
        "/api/plugins/dummy/instances",
        json={"action": "add", "instance": {"enabled": True, "url": "http://x"}},
    )
    assert rv.status_code == 400


def test_api_backups_list_and_create(client, login, tmp_path, monkeypatch):
    # Setup CONFIG_DIR and create a sample backup file
    cfg = tmp_path / "config"
    bdir = cfg / "backups"
    bdir.mkdir(parents=True)
    f = bdir / "b1.zip"
    f.write_bytes(b"hello")
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    login()
    rv = client.get("/api/backups")
    assert rv.status_code == 200
    data = rv.get_json()
    assert any(b["name"] == "b1.zip" for b in data.get("backups", []))

    # patch _create_backup_file to return a filename
    def fake_create(config_root, backups_dir, prefix=""):
        return "generated.zip"

    # Patch the underlying helper used by the nested create function in the
    # factory module (the nested _create_backup_file calls the module-level
    # `create_backup_file`), so override that implementation.
    monkeypatch.setattr("researcharr.factory.create_backup_file", fake_create, raising=False)
    rv2 = client.post("/api/backups/create")
    assert rv2.status_code == 200
    assert rv2.get_json().get("name") == "generated.zip"


def test_api_backups_import_upload(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    (cfg / "backups").mkdir(parents=True)
    login()
    data = {
        "file": (io.BytesIO(b"zipdata"), "test.zip"),
    }
    rv = client.post("/api/backups/import", data=data, content_type="multipart/form-data")
    assert rv.status_code == 200
    assert rv.get_json().get("name") == "test.zip"
