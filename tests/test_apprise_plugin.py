import sys
from types import SimpleNamespace

import pytest


def make_fake_apprise(monkeypatch):
    class FakeApprise:
        def __init__(self):
            self.added = []

        def add(self, u):
            self.added.append(u)
            return True

        def notify(self, title=None, body=None):
            # Simulate success
            return True

    fake_mod = SimpleNamespace(Apprise=FakeApprise)
    monkeypatch.setitem(sys.modules, "apprise", fake_mod)


def test_apprise_validate_and_sync(monkeypatch):
    make_fake_apprise(monkeypatch)
    from plugins.notifications.example_apprise import Plugin

    cfg = {"urls": ["apprise://mock"], "test": True}
    p = Plugin(cfg)

    v = p.validate()
    assert v.get("success") is True

    s = p.sync()
    assert s.get("success") is True


def test_apprise_blueprint_send(monkeypatch):
    make_fake_apprise(monkeypatch)
    from flask import Flask

    from plugins.notifications.example_apprise import Plugin

    cfg = {"urls": ["apprise://mock"]}
    p = Plugin(cfg)
    bp = p.blueprint()

    app = Flask(__name__)
    app.register_blueprint(bp)

    client = app.test_client()
    r = client.post("/plugin/apprise/send", json={"title": "t", "body": "b"})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("success") is True
