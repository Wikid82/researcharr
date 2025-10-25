from researcharr.plugins.registry import PluginRegistry


def test_discover_local(tmp_path, monkeypatch):
    # create a fake plugin file in a temporary plugins directory
    plugin_code = """
PLUGIN_NAME = "dummy"
class Plugin:
    def __init__(self, cfg):
        self.cfg = cfg
    def validate(self):
        return {"success": True}
"""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    p = plugins_dir / "dummy.py"
    p.write_text(plugin_code)

    reg = PluginRegistry()
    reg.discover_local(str(plugins_dir))
    assert "dummy" in reg.list_plugins()

    inst = reg.create_instance("dummy", {"name": "x"})
    assert inst.cfg["name"] == "x"
