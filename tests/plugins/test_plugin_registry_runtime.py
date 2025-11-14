import pytest

from researcharr.plugins.registry import PluginRegistry


class SamplePlugin:
    def __init__(self, config):
        self.config = config


def test_plugin_registry_basic_operations(tmp_path):
    reg = PluginRegistry()
    reg.register("sample", SamplePlugin)
    assert reg.get("sample") is SamplePlugin
    inst = reg.create_instance("sample", {"k": "v"})
    assert isinstance(inst, SamplePlugin)
    assert inst.config == {"k": "v"}
    assert "sample" in reg.list_plugins()


def test_plugin_registry_missing_plugin(tmp_path):
    reg = PluginRegistry()
    reg.register("sample", SamplePlugin)
    with pytest.raises(KeyError):
        reg.create_instance("other", {})
