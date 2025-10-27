"""Compatibility subpackage for `researcharr.plugins`.

The project historically exposed plugin example modules under
``researcharr.plugins.*``. The repository also contains a top-level
``plugins`` package (for discovery). To remain compatible with tests
and external imports, provide a light shim package here that re-exports
selected example modules from the real location.
"""

from importlib import import_module

__all__ = []

try:
    # Try importing the example sonarr plugin from the canonical
    # location under `plugins.media` and expose it under this package.
    sonarr_mod = import_module("plugins.media.example_sonarr")
    PLUGIN_NAME = getattr(sonarr_mod, "PLUGIN_NAME", None)
    Plugin = getattr(sonarr_mod, "Plugin", None)
    __all__.append("example_sonarr")
except Exception:
    # If import fails, keep shim minimal; tests that need the plugin will
    # try to load via the explicit file-location fallback implemented in
    # `researcharr.plugins.example_sonarr`.
    pass
