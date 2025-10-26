from flask import Flask


def register_and_call(bp):
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    return client.get("/")  # simple check; endpoint tests will call specific routes


def test_radarr_items_endpoint():
    from plugins.media.example_radarr import Plugin

    p = Plugin({})
    bp = p.blueprint()
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    r = client.get("/plugin/radarr/items")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("success") is True


def test_sonarr_items_endpoint():
    from plugins.media.example_sonarr import Plugin

    p = Plugin({})
    bp = p.blueprint()
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    r = client.get("/plugin/sonarr/items")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("success") is True


def test_nzbget_queue_endpoint():
    from plugins.clients.example_nzbget import Plugin

    p = Plugin({})
    app = Flask(__name__)
    app.register_blueprint(p.blueprint())
    client = app.test_client()
    r = client.get("/plugin/nzbget/queue")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("success") is True
