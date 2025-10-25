import json

from researcharr.factory import create_app


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
