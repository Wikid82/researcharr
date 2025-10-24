"""Plugin package for third-party integrations (sonarr, radarr, etc.).

This package contains the plugin base class, a simple registry/loader,
and example plugin modules. Plugins should subclass BasePlugin and
implement the required methods.
"""

__all__ = ["base", "registry", "example_sonarr"]
