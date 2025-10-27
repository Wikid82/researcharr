import os


def login_client(app):
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=True,
    )
    return client


def test_api_logs_stream_initial_tail_and_exit(tmp_path, monkeypatch):
    # prepare temp log file
    logf = tmp_path / "app.log"
    lines = [f"streamline {i}" for i in range(6)]
    logf.write_text("\n".join(lines) + "\n")

    monkeypatch.setenv("WEBUI_LOG", str(logf))
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    # cause the generator to exit after sending initial tail by making
    # time.sleep raise GeneratorExit when invoked in the streaming loop
    import time as _time

    def raise_genexit(_):
        raise GeneratorExit()

    monkeypatch.setattr(_time, "sleep", raise_genexit)

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # request a short initial tail; the patched sleep will stop the stream
    r = client.get("/api/logs/stream?lines=3")
    assert r.status_code == 200
    body = r.data.decode("utf-8", errors="ignore")
    # SSE framing should include 'data: ' prefixed lines
    assert "data: streamline 5" in body
    assert "data: streamline 3" in body
