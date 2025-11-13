"""Runtime shim for `researcharr.plugins.registry`.

This module prefers the repository-top `plugins.registry` implementation
when available (normal source checkout layout). When running in an
environment where that package isn't importable, provide a small
fallback `PluginRegistry` implementation so editors and type checkers
can resolve the symbol without failing imports.

We support a temporary, opt-in short-circuit that disables plugin
loading entirely. Set the environment variable `RESEARCHARR_DISABLE_PLUGINS`
to `1`, `true` or `True` to disable plugin discovery. This is intended
as a safe, reversible measure to help CI and test triage while plugin
work is reworked in a follow-up issue.
"""

from __future__ import annotations

import os as _os

if _os.getenv("RESEARCHARR_DISABLE_PLUGINS") in ("1", "true", "True"):

    class PluginRegistry:
        def __init__(self) -> None:
            return

        def register(self, name: str, cls: type) -> None:
            return

        def get(self, name: str):
            return None

        def discover_local(self, plugins_dir: str) -> None:
            return

        def create_instance(self, plugin_name: str, config: dict):
            raise KeyError("Plugins disabled via RESEARCHARR_DISABLE_PLUGINS")

        def list_plugins(self) -> list[str]:
            return []

    __all__ = ["PluginRegistry"]
else:
    try:  # prefer the repository-level implementation
        from plugins.registry import PluginRegistry  # type: ignore

        try:
            import os as _os

            if _os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                print("[registry-shim] using import plugins.registry")
        except Exception:
            pass
    except Exception:  # pragma: no cover - robust fallback to repo file
        # If importing the top-level package fails (e.g., sys.path/state differs
        # under certain runners), attempt to load the repository implementation
        # directly from its source file. Only fall back to a minimal stub if that
        # also fails. This keeps unit tests for discovery working inside containers.
        import importlib.util
        import os
        from typing import Any

        _PluginRegistryResolved = None
        try:
            _here = os.path.abspath(os.path.dirname(__file__))
            # Walk upward until we find a real repository root containing
            # 'plugins/registry.py'. The nested package layout lives at
            # '<repo>/researcharr/researcharr/plugins/registry.py'. Ascending
            # parents lets us resolve the true repo root ('<repo>') when running
            # inside containers where the previous heuristic stopped too early
            # (yielding '<repo>/researcharr'). Limit depth to avoid infinite loops.
            _search = os.path.abspath(os.path.join(_here, os.pardir))
            _impl_path = None
            for _i in range(6):
                _cand = os.path.join(_search, "plugins", "registry.py")
                if os.path.isfile(_cand):
                    _impl_path = _cand
                    break
                _next = os.path.abspath(os.path.join(_search, os.pardir))
                if _next == _search:
                    break
                _search = _next
            if _impl_path and os.path.isfile(_impl_path):
                _spec = importlib.util.spec_from_file_location("plugins.registry", _impl_path)
                if _spec and _spec.loader:
                    _mod = importlib.util.module_from_spec(_spec)
                    _spec.loader.exec_module(_mod)  # type: ignore[arg-type]
                    _PluginRegistryResolved = getattr(_mod, "PluginRegistry", None)
                    try:
                        import os as _os

                        if _os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                            print(
                                f"[registry-shim] loaded from file {_impl_path}, ok={_PluginRegistryResolved is not None}"
                            )
                    except Exception:
                        pass
        except Exception as _e:
            try:
                import os as _os

                if _os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                    print(f"[registry-shim] fallback file load failed: {_e}")
            except Exception:
                pass
            _PluginRegistryResolved = None

        if _PluginRegistryResolved is not None:
            PluginRegistry = _PluginRegistryResolved  # type: ignore[assignment]
        else:
            try:
                import os as _os

                if _os.getenv("RESEARCHARR_DEBUG_REGISTRY_SHIM"):
                    print("[registry-shim] using built-in full PluginRegistry implementation")
            except Exception:
                pass

            class PluginRegistry:
                def __init__(self) -> None:
                    self._plugins: dict[str, type[Any]] = {}

                def register(self, name: str, cls: type[Any]) -> None:
                    self._plugins[name] = cls

                def get(self, name: str) -> Any:
                    return self._plugins.get(name)

                def discover_local(self, plugins_dir: str) -> None:
                    import importlib.util as _ilu
                    import os as _os

                    if not _os.path.isdir(plugins_dir):
                        return
                    for root, _dirs, files in _os.walk(plugins_dir):
                        rel = _os.path.relpath(root, plugins_dir)
                        depth = 0 if rel == "." else len(rel.split(_os.sep))
                        if depth > 1:
                            continue
                        parent = None if rel == "." else rel
                        for fn in files:
                            if not fn.endswith(".py") or fn.startswith("_"):
                                continue
                            path = _os.path.join(root, fn)
                            name = _os.path.splitext(fn)[0]
                            mod_name = f"_researcharr_local_plugin_{name}_{abs(hash(path))}"
                            spec = _ilu.spec_from_file_location(mod_name, path)
                            if spec is None or spec.loader is None:
                                continue
                            mod = _ilu.module_from_spec(spec)
                            loader = spec.loader
                            assert loader is not None
                            try:
                                loader.exec_module(mod)
                            except Exception:
                                continue
                            plugin_name = getattr(mod, "PLUGIN_NAME", None)
                            plugin_cls = getattr(mod, "Plugin", None)
                            if not plugin_name or not plugin_cls:
                                continue
                            explicit_cat = getattr(mod, "CATEGORY", None) or getattr(
                                plugin_cls, "category", None
                            )
                            if explicit_cat:
                                plugin_cls.category = explicit_cat
                            elif parent:
                                plugin_cls.category = parent
                            else:
                                plugin_cls.category = getattr(plugin_cls, "category", "plugins")
                            self.register(plugin_name, plugin_cls)

                def create_instance(self, plugin_name: str, config: dict) -> Any:
                    cls = self.get(plugin_name)
                    if not cls:
                        raise KeyError(f"Unknown plugin: {plugin_name}")
                    return cls(config)

                def list_plugins(self) -> list[str]:
                    return list(self._plugins.keys())

        __all__ = ["PluginRegistry"]
