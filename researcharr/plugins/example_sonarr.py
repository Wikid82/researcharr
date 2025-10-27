"""Compatibility shim for the example Sonarr plugin.

Tests and external code import ``researcharr.plugins.example_sonarr``.
The canonical implementation lives under ``plugins.media.example_sonarr``
in this repository. This module attempts to import the canonical
location first and falls back to loading the file by path if needed.
"""

import importlib
import importlib.util
import os
from types import ModuleType
from typing import Any


def _load_module() -> ModuleType:
    # Prefer the namespaced top-level package location
    try:
        return importlib.import_module("plugins.media.example_sonarr")
    except Exception:
        # Fallback: load by file path relative to repository root. This
        # handles environments where the package layout differs.
        base = os.path.dirname(os.path.dirname(__file__))
        # repo_root/researcharr/plugins -> go up to repo root then plugins/media
        repo_root = os.path.dirname(base)
        candidate = os.path.join(repo_root, "plugins", "media", "example_sonarr.py")
        if os.path.exists(candidate):
            spec = importlib.util.spec_from_file_location(
                "researcharr.plugins.example_sonarr", candidate
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        raise ImportError(
            "Could not import example_sonarr from plugins.media or fallback path"
        )


_mod = _load_module()

# Re-export the expected symbols
PLUGIN_NAME: Any = getattr(_mod, "PLUGIN_NAME", None)
Plugin: Any = getattr(_mod, "Plugin", None)

__all__ = ["PLUGIN_NAME", "Plugin"]
