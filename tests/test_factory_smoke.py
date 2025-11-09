import os
import tempfile

from researcharr import factory


def test_create_app_defaults(monkeypatch):
    # Ensure CONFIG_DIR is a temp dir for isolation
    td = tempfile.TemporaryDirectory()
    monkeypatch.setenv("CONFIG_DIR", td.name)

    app = factory.create_app()
    # Basic app invariants
    assert app is not None
    assert hasattr(app, "config_data")
    cfg = app.config_data
    assert isinstance(cfg, dict)
    assert "general" in cfg
    # default user exists
    assert cfg.get("user") is not None
    # session secret present (dev fallback)
    assert app.secret_key == os.getenv("SECRET_KEY", "dev")

    # metrics present and basic counters
    assert hasattr(app, "metrics")
    assert "requests_total" in app.metrics

    td.cleanup()
