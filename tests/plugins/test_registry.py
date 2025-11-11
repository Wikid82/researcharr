import os
import tempfile
import textwrap

import pytest

from researcharr.plugins.registry import PluginRegistry


def write_plugin(path: str, filename: str, content: str):
    with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def test_registry_register_and_get():
    reg = PluginRegistry()

    class DummyPlugin:
        def __init__(self, config):
            self.config = config

    reg.register("dummy", DummyPlugin)
    assert reg.get("dummy") is DummyPlugin
    assert "dummy" in reg.list_plugins()


def test_registry_create_instance_success():
    reg = PluginRegistry()

    class DummyPlugin:
        def __init__(self, config):
            self.config = config

    reg.register("dummy", DummyPlugin)
    inst = reg.create_instance("dummy", {"x": 1})
    assert isinstance(inst, DummyPlugin)
    assert inst.config["x"] == 1


def test_registry_create_instance_missing():
    reg = PluginRegistry()
    with pytest.raises(KeyError):
        reg.create_instance("missing", {})


def test_discover_local_top_level_and_category():
    reg = PluginRegistry()
    with tempfile.TemporaryDirectory() as tmp:
        # Top-level plugin: expect category default 'plugins'
        write_plugin(
            tmp,
            "simple.py",
            """
            PLUGIN_NAME = 'simple'
            class Plugin:
                category = 'initial'
                def __init__(self, config):
                    self.config = config
            """,
        )
        # Category subdir plugin: expect category directory name
        media_dir = os.path.join(tmp, "media")
        os.makedirs(media_dir)
        write_plugin(
            media_dir,
            "media_plugin.py",
            """
            PLUGIN_NAME = 'media_plugin'
            class Plugin:
                def __init__(self, config):
                    self.config = config
            """,
        )
        # Deeper nested should be ignored
        inner = os.path.join(media_dir, "inner")
        os.makedirs(inner)
        write_plugin(
            inner,
            "ignored.py",
            """
            PLUGIN_NAME = 'ignored'
            class Plugin:
                def __init__(self, config):
                    self.config = config
            """,
        )

        reg.discover_local(tmp)
        names = set(reg.list_plugins())
        assert names == {"simple", "media_plugin"}
        # Validate categories assigned
        simple_cls = reg.get("simple")
        media_cls = reg.get("media_plugin")
        assert simple_cls.category in {"initial", "plugins"}
        assert media_cls.category == "media"


def test_discover_local_explicit_category_override():
    reg = PluginRegistry()
    with tempfile.TemporaryDirectory() as tmp:
        write_plugin(
            tmp,
            "explicit.py",
            """
            PLUGIN_NAME = 'explicit'
            CATEGORY = 'overridden'
            class Plugin:
                def __init__(self, config):
                    self.config = config
            """,
        )
        reg.discover_local(tmp)
        cls = reg.get("explicit")
        assert cls.category == "overridden"


def test_plugins_package_init_imports():
    # Ensure attributes exposed by __all__ are importable
    import researcharr.plugins as plugins_pkg

    for name in ["base", "registry", "clients", "media", "notifications", "scrapers"]:
        assert hasattr(plugins_pkg, name)
