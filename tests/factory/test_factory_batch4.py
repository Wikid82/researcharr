import io
import zipfile


def test_api_updates_ignore_and_unignore(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    login()

    # invalid mode
    rv = client.post("/api/updates/ignore", json={"mode": "bad"})
    assert rv.status_code == 400

    # ignore by release
    rv2 = client.post("/api/updates/ignore", json={"mode": "release", "release_tag": "v1.2.3"})
    assert rv2.status_code == 200
    data = rv2.get_json()
    assert data.get("result") == "ok"
    # ensure file persisted
    assert (cfg / "updates.yml").exists()

    # unignore clears the file entries
    rv3 = client.post("/api/updates/unignore")
    assert rv3.status_code == 200


def test_backups_create_and_import_and_restore(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    login()

    # Monkeypatch the underlying create_backup_file to a simple stub
    from researcharr import factory

    monkeypatch.setattr(
        factory, "create_backup_file", lambda a, b, prefix="": "test-backup.zip", raising=False
    )

    # create should return ok and a basename
    rv = client.post("/api/backups/create")
    assert rv.status_code == 200
    d = rv.get_json()
    assert d.get("result") == "ok"
    assert d.get("name") == "test-backup.zip"

    # import: missing file -> 400
    rv2 = client.post("/api/backups/import", data={})
    assert rv2.status_code == 400

    # import: send a small zip file
    backups_dir = cfg / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("config/config.yml", "hello: world")
    buf.seek(0)
    data = {"file": (buf, "imported.zip")}
    rv3 = client.post("/api/backups/import", data=data, content_type="multipart/form-data")
    assert rv3.status_code == 200
    j = rv3.get_json()
    assert j.get("result") == "ok"
    assert (backups_dir / "imported.zip").exists()

    # restore: create a zip file on disk and call restore
    fname = "to_restore.zip"
    fpath = backups_dir / fname
    with zipfile.ZipFile(fpath, "w") as zf:
        zf.writestr("config/config.yml", "restored: yes")

    # avoid pre-restore creation by stubbing create_backup_file to None
    monkeypatch.setattr(factory, "create_backup_file", lambda a, b, prefix="": None, raising=False)
    rv4 = client.post(f"/api/backups/restore/{fname}")
    assert rv4.status_code == 200
    jr = rv4.get_json()
    assert jr.get("result") == "restored"
    # restored file should exist in CONFIG_DIR
    assert (cfg / "config.yml").exists() or (cfg / "config" / "config.yml").exists()


def test_plugin_instances_actions_and_invalid(client, login, tmp_path, monkeypatch):
    # Setup CONFIG_DIR so persistence works
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))

    # Dummy registry that advertises a plugin but validates creation
    class DummyReg:
        def __init__(self):
            self._plugins = {"dummy": object}

        def list_plugins(self):
            return ["dummy"]

        def get(self, name):
            return object if name == "dummy" else None

        def create_instance(self, name, inst):
            # return a simple object with validate/sync if needed
            class P:
                def __init__(self, cfg):
                    self.cfg = cfg

                def validate(self):
                    return True

                def sync(self):
                    return True

                def blueprint(self):
                    return None

            return P(inst)

    client.application.plugin_registry = DummyReg()
    login()

    # unknown action
    rv = client.post("/api/plugins/dummy/instances", json={"action": "bogus"})
    assert rv.status_code == 400

    # add invalid instance (enabled but missing url/api_key)
    rv2 = client.post(
        "/api/plugins/dummy/instances", json={"action": "add", "instance": {"enabled": True}}
    )
    assert rv2.status_code == 400

    # add valid instance
    inst = {"enabled": True, "url": "https://example.local", "api_key": "k"}
    rv3 = client.post("/api/plugins/dummy/instances", json={"action": "add", "instance": inst})
    assert rv3.status_code == 200
    j = rv3.get_json()
    assert j.get("result") == "ok"
    # persisted file
    assert (cfg / "plugins" / "dummy.yml").exists()


def test_plugin_validate_and_sync_unknown(client, login):
    # no registry -> unknown plugin
    client.application.plugin_registry = None
    login()
    rv = client.post("/api/plugins/foo/validate/0")
    assert rv.status_code == 404
    rv2 = client.post("/api/plugins/foo/sync/0")
    assert rv2.status_code == 404


def test_general_settings_regen_api(client, login, monkeypatch):
    # ensure regen_api sets api_key_hash and attempts to persist
    from researcharr import factory

    # stub webui.save_user_config so it doesn't perform IO
    # Allow setting `webui` even when the attribute is not present on the
    # module (ModuleProxy behavior in CI can leave some attributes missing).
    monkeypatch.setattr(
        factory,
        "webui",
        type("W", (), {"save_user_config": lambda *a, **k: None, "load_user_config": lambda: {}}),
        raising=False,
    )
    login()
    rv = client.post("/settings/general", data={"regen_api": "1"})
    assert rv.status_code == 200
    # api_key_hash should be set in app config
    assert client.application.config_data.get("general", {}).get("api_key_hash")
