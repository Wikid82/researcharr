import importlib
import importlib.util
import os
from typing import Dict, List, Type

from researcharr.plugins.base import BasePlugin


class PluginRegistry:
    def __init__(self):
        # mapping plugin_name -> plugin class
        self._plugins: Dict[str, Type[BasePlugin]] = {}

    def register(self, name: str, cls: Type[BasePlugin]):
        self._plugins[name] = cls

    def get(self, name: str):
        return self._plugins.get(name)

    def discover_local(self, plugins_dir: str):
        """Discover plugin modules in a local plugins directory.

        Each plugin module should define `PLUGIN_NAME` and `Plugin` class.
        """
        if not os.path.isdir(plugins_dir):
            return
        for fn in os.listdir(plugins_dir):
            if not fn.endswith(".py") or fn.startswith("_"):
                continue
            path = os.path.join(plugins_dir, fn)
            name = os.path.splitext(fn)[0]
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            loader = spec.loader
            assert loader is not None
            try:
                loader.exec_module(mod)
            except Exception:
                continue
            plugin_name = getattr(mod, "PLUGIN_NAME", None)
            plugin_cls = getattr(mod, "Plugin", None)
            if plugin_name and plugin_cls:
                self.register(plugin_name, plugin_cls)

    def create_instance(self, plugin_name: str, config: Dict):
        cls = self.get(plugin_name)
        if not cls:
            raise KeyError(f"Unknown plugin: {plugin_name}")
        return cls(config)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())
