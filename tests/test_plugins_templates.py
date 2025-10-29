import os

from researcharr.factory import create_app


def test_example_plugin_templates_load(monkeypatch):
    """Smoke test: ensure example plugin YAML templates in repo/config/plugins
    are loaded (as empty lists) into app.config_data when CONFIG_DIR points
    at the repo config directory.
    """
    repo_root = os.getcwd()
    config_dir = os.path.join(repo_root, "config")
    # Point the app at the repo config dir (where we've added templates)
    monkeypatch.setenv("CONFIG_DIR", config_dir)
    app = create_app()
    # A few known plugin names should exist in config_data (as lists)
    expected = [
        "radarr",
        "sonarr",
        "apprise",
    ]
    for name in expected:
        assert name in app.config_data
        assert isinstance(app.config_data.get(name), list)
