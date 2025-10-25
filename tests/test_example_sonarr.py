import json

from flask import Flask

from researcharr.plugins.example_sonarr import Plugin


def test_example_sonarr_blueprint():
    pl = Plugin({"name": "test", "url": "http://example", "api_key": "key"})
    bp = pl.blueprint()
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    resp = client.get("/plugin/sonarr/info")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get("plugin") == "sonarr"
    assert data.get("config")["name"] == "test"
