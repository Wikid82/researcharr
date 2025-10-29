"""Runtime shim for `researcharr.plugins.registry`.

This module prefers the repository-top `plugins.registry` implementation
when available (normal source checkout layout). When running in an
environment where that package isn't importable, provide a small
fallback `PluginRegistry` implementation so editors and type checkers
can resolve the symbol without failing imports.
"""
from __future__ import annotations

try:  # prefer the repository-level implementation
    from plugins.registry import PluginRegistry  # type: ignore
except Exception:  # pragma: no cover - fallback for editor/type-checker
    from typing import Any, Dict, List

    class PluginRegistry:  # simple local fallback used only when the real
        """Fallback PluginRegistry exposing the minimal runtime API.

        This does not aim to reproduce full behavior; it's a safe stub that
        satisfies importers and static analysis.
        """

        def __init__(self) -> None:
            self._plugins: Dict[str, type[Any]] = {}

        def register(self, name: str, cls: type[Any]) -> None:
            self._plugins[name] = cls

        def get(self, name: str) -> Any:
            return self._plugins.get(name)

        def discover_local(self, plugins_dir: str) -> None:
            # No-op fallback; real implementation discovers files on disk.
            return None

        def create_instance(self, plugin_name: str, config: Dict) -> Any:
            cls = self.get(plugin_name)
            if not cls:
                raise KeyError(f"Unknown plugin: {plugin_name}")
            return cls(config)

        def list_plugins(self) -> List[str]:

            return list(self._plugins.keys())


__all__ = ["PluginRegistry"]
