import json

from researcharr.factory import create_app
import os
import tempfile


def test_api_version_defaults():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/version")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    # The endpoint should always return at least these keys
    assert "version" in data
    assert "build" in data
    assert "sha" in data


def test_api_version_from_file(monkeypatch):
    # Create temporary version file and point the app at it
    tf = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    try:
        tf.write("version=1.2.3\n")
        tf.write("build=42\n")
        tf.write("sha=deadbeef\n")
        tf.flush()
        monkeypatch.setenv("RESEARCHARR_VERSION_FILE", tf.name)

        app = create_app()
        client = app.test_client()
        resp = client.get("/api/version")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data.get("version") == "1.2.3"
        assert data.get("build") == "42"
        assert data.get("sha") == "deadbeef"
    finally:
        try:
            tf.close()
        except Exception:
            pass
        try:
            os.unlink(tf.name)
        except Exception:
            pass
