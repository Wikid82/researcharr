from collections.abc import Generator

import pytest

from researcharr import factory


@pytest.fixture
def app(monkeypatch, tmp_path) -> Generator:
    # Ensure CONFIG_DIR is isolated for tests
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setenv("CONFIG_DIR", str(cfg))
    # Create the app under test
    app = factory.create_app()
    app.testing = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(username: str = "admin", password: str = "password"):
        return client.post("/login", data={"username": username, "password": password})

    return _login
