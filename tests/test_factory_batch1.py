from researcharr import factory


def make_client():
    app = factory.create_app()
    app.config["TESTING"] = True
    return app.test_client(), app


def login(client):
    return client.post("/login", data={"username": "admin", "password": "password"})


def test_index_redirects_to_setup():
    client, app = make_client()
    rv = client.get("/")
    assert rv.status_code in (302, 303)
    # Location may be absolute; check suffix
    assert rv.headers["Location"].endswith("/setup")


def test_login_redirects_to_general_settings():
    client, app = make_client()
    rv = login(client)
    assert rv.status_code in (302, 303)
    assert rv.headers["Location"].endswith("/settings/general")


def test_api_tasks_post_requires_json():
    client, app = make_client()
    login(client)
    # posting without application/json should return 415
    rv = client.post("/api/tasks", data="{}")
    assert rv.status_code == 415


def test_api_tasks_post_json_created():
    client, app = make_client()
    login(client)
    rv = client.post("/api/tasks", json={"name": "t1"})
    assert rv.status_code == 201
    rv.get_json()

    def test_index_redirects_to_setup(client):
        rv = client.get("/")
        assert rv.status_code in (302, 303)
        assert rv.headers["Location"].endswith("/setup")

    def test_login_redirects_to_general_settings(client, login):
        rv = login()
        assert rv.status_code in (302, 303)
        assert rv.headers["Location"].endswith("/settings/general")

    def test_api_tasks_post_requires_json(client, login):
        login()
        rv = client.post("/api/tasks", data="{}")
        assert rv.status_code == 415

    def test_api_tasks_post_json_created(client, login):
        login()
        rv = client.post("/api/tasks", json={"name": "t1"})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["result"] == "created"
        assert data["task"]["name"] == "t1"

    def test_api_logs_when_missing_file_returns_empty(client, login, monkeypatch, tmp_path):
        login()
        tmp = tmp_path / "no_log.log"
        monkeypatch.setenv("WEBUI_LOG", str(tmp))
        rv = client.get("/api/logs")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["content"] == ""
        assert isinstance(data["meta"], dict)

    def test_api_version_reads_file(client, tmp_path, monkeypatch):
        p = tmp_path / "VERSION"
        p.write_text("version=1.2.3\nbuild=7\n")
        monkeypatch.setenv("RESEARCHARR_VERSION_FILE", str(p))
        rv = client.get("/api/version")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data.get("version") == "1.2.3"
        assert data.get("build") == "7"

    def test_metrics_before_request_increment(client):
        rv1 = client.get("/metrics")
        assert rv1.status_code == 200
        data1 = rv1.get_json()
        rv2 = client.get("/metrics")
        data2 = rv2.get_json()
        assert int(data2.get("requests_total", 0)) >= int(data1.get("requests_total", 0)) + 1
