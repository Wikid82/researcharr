import json

from researcharr.factory import create_app


def test_api_plugins_endpoint():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "plugins" in data
    # Example sonarr plugin should be discovered by registry discovery
    names = [p["name"] for p in data["plugins"]]
    assert "sonarr" in names
