"""Compatibility shim for the example Sonarr plugin.

Tests and older imports reference `researcharr.plugins.example_sonarr.Plugin`.
Import and re-export the plugin implementation from the canonical location
under the top-level `plugins` package.
"""

from plugins.media.example_sonarr import Plugin  # re-export  # noqa: F401
