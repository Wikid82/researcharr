"""Plugin package for third-party integrations (sonarr, radarr, etc.).

This package contains the plugin base class, a simple registry/loader,
and example plugin modules. Plugins should subclass BasePlugin and
implement the required methods.
"""

# Import submodules to make them accessible as package attributes
from . import base, clients, media, notifications, registry, scrapers

__all__ = ["base", "registry", "clients", "media", "notifications", "scrapers"]
