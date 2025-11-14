import importlib
import importlib.util
import os

from researcharr.plugins.base import BasePlugin


class PluginRegistry:
    def __init__(self):
        # mapping plugin_name -> plugin class
        self._plugins: dict[str, type[BasePlugin]] = {}

    def register(self, name: str, cls: type[BasePlugin]):
        self._plugins[name] = cls

    def get(self, name: str):
        return self._plugins.get(name)

    def discover_local(self, plugins_dir: str):
        """Discover plugin modules in a local plugins directory.

        Each plugin module should define `PLUGIN_NAME` and `Plugin` class.
        """
        if not os.path.isdir(plugins_dir):
            return

        # Walk plugins_dir and discover .py files. Prefer immediate
        # subdirectory name as the plugin category (e.g. plugins/media/* ->
        # category 'media') but allow module/class-level category to
        # override.
        for root, dirs, files in os.walk(plugins_dir):
            # Limit discovery to top-level and one-level deep (category
            # folders). Compute relative depth from plugins_dir.
            rel = os.path.relpath(root, plugins_dir)
            depth = 0 if rel == "." else len(rel.split(os.sep))
            if depth > 1:
                # skip deeper nested folders
                continue

            parent = None if rel == "." else rel

            for fn in files:
                if not fn.endswith(".py") or fn.startswith("_"):
                    continue
                path = os.path.join(root, fn)
                name = os.path.splitext(fn)[0]
                # Use a unique module name to avoid collisions with the
                # repository's real 'plugins' package. Collisions can occur
                # under test when loading from a temporary directory.
                mod_name = f"_researcharr_local_plugin_{name}_{abs(hash(path))}"
                spec = importlib.util.spec_from_file_location(mod_name, path)
                if spec is None or spec.loader is None:
                    # noisy debug when enabled via env for container diagnosis
                    if os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                        print(f"[registry-discover] skip spec load path={path}")
                    continue
                mod = importlib.util.module_from_spec(spec)
                loader = spec.loader
                assert loader is not None
                try:
                    loader.exec_module(mod)
                except Exception as e:
                    # skip modules that fail to import during discovery
                    if os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                        print(f"[registry-discover] import failed path={path} err={e}")
                    continue

                plugin_name = getattr(mod, "PLUGIN_NAME", None)
                plugin_cls = getattr(mod, "Plugin", None)
                if not plugin_name or not plugin_cls:
                    if os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                        print(f"[registry-discover] missing PLUGIN_NAME/Plugin path={path}")
                    continue

                # Determine category: explicit module-level or class attr
                explicit_cat = getattr(mod, "CATEGORY", None) or getattr(
                    plugin_cls, "category", None
                )
                if explicit_cat:
                    plugin_cls.category = explicit_cat
                elif parent:
                    plugin_cls.category = parent
                else:
                    plugin_cls.category = getattr(plugin_cls, "category", "plugins")

                if os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                    print(
                        f"[registry-discover] registered name={plugin_name} cat={getattr(plugin_cls, 'category', None)} path={path} mod={mod_name}"
                    )
                self.register(plugin_name, plugin_cls)

    def create_instance(self, plugin_name: str, config: dict):
        cls = self.get(plugin_name)
        if not cls:
            raise KeyError(f"Unknown plugin: {plugin_name}")
        return cls(config)

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())
