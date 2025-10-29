"""Compatibility re-export so callers can import `plugins.example_sonarr`.

The canonical example Sonarr plugin lives under `plugins.media.example_sonarr`.
Expose it directly at `plugins.example_sonarr` to simplify imports used by
tests and external tooling.
"""

from .media.example_sonarr import PLUGIN_NAME, Plugin  # noqa: F401

__all__ = ["PLUGIN_NAME", "Plugin"]
