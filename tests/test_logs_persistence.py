import yaml


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_loglevel_persisted_to_config(tmp_path, monkeypatch):
    # point CONFIG_DIR to a temp dir
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    r = client.post("/logs", data={"LogLevel": "DEBUG"})
    assert r.status_code == 200

    gen_file = tmp_path / "general.yml"
    assert gen_file.exists()
    data = yaml.safe_load(gen_file.read_text())
    assert data.get("LogLevel") == "DEBUG"
