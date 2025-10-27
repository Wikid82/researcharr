import threading
import time


def login_client(app):
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    return client


def test_sse_stream_yields_appended_lines(tmp_path, monkeypatch):
    # prepare log with initial content
    logf = tmp_path / "app.log"
    logf.write_text("line 0\n")

    monkeypatch.setenv("WEBUI_LOG", str(logf))
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    # make time.sleep short so the streaming loop checks often
    import time as _time

    def short_sleep(s):
        # small real sleep to yield to other thread
        time.sleep(0.01)

    monkeypatch.setattr(_time, "sleep", short_sleep)

    from researcharr.factory import create_app

    app = create_app()
    client = login_client(app)

    # helper to append lines after a small delay
    def appender():
        time.sleep(0.05)
        with open(str(logf), "a") as fh:
            fh.write("line 1\n")
            fh.flush()
        time.sleep(0.05)
        with open(str(logf), "a") as fh:
            fh.write("line 2\n")
            fh.flush()

    t = threading.Thread(target=appender, daemon=True)
    t.start()

    # request streaming response (buffered=False to iterate)
    resp = client.get("/api/logs/stream?lines=0", buffered=False)
    # iterate and collect a few chunks
    seen = ""
    for chunk in resp.iter_encoded():
        try:
            s = chunk.decode("utf-8")
        except Exception:
            s = str(chunk)
        seen += s
        if "line 2" in seen:
            break

    assert "data: line 1" in seen
    assert "data: line 2" in seen
