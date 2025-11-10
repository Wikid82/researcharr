def test_setup_generates_api_and_persists(client, tmp_path, monkeypatch):
    # ensure CONFIG_DIR is isolated and stub webui
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    from researcharr import factory

    class W:
        def save_user_config(self, *a, **k):
            # no-op persistence
            return None

    monkeypatch.setattr(factory, "webui", W())
    # create app via client fixture already done; post to setup
    rv = client.post(
        "/setup", data={"username": "u", "password": "longpass", "confirm": "longpass"}
    )
    # success path renders a template (200)
    assert rv.status_code == 200
    assert client.application.config.get("USER_CONFIG_EXISTS") is True


def test_reset_password_flow(client, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    monkeypatch.setenv("WEBUI_RESET_TOKEN", "tok")
    rv = client.post(
        "/reset-password",
        data={"username": "admin", "token": "tok", "password": "newpass", "confirm": "newpass"},
    )
    # successful reset redirects to login
    assert rv.status_code in (302, 200)
    # password updated in in-memory config
    assert client.application.config_data["user"]["password"] == "newpass"


def test_logs_page_post_sets_loglevel(client, login):
    login()
    rv = client.post("/logs", data={"LogLevel": "DEBUG"})
    assert rv.status_code == 200
    assert client.application.config_data.get("general", {}).get("LogLevel") == "DEBUG"


def test_api_storage_endpoint(client, login, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    login()
    rv = client.get("/api/storage")
    assert rv.status_code == 200
    j = rv.get_json()
    assert "paths" in j and isinstance(j.get("paths"), list)
