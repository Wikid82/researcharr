from typing import Any, Dict, Optional

from flask import Blueprint


class BasePlugin:
    """Base class for researcharr integrations.

    Subclasses should implement `validate`, `sync`, `health`, and may
    optionally provide a Flask `blueprint` to add UI routes.
    """

    name: str = "base"

    def __init__(self, instance_config: Dict[str, Any] | None = None):
        """Initialize plugin instance.

        Tests often instantiate example plugins without passing a config. To
        be permissive for tests and IDE analysis, accept None and normalize to
        an empty dict.
        """
        self.config = instance_config or {}

    def validate(self) -> Dict[str, Any]:
        """Validate instance configuration (connectivity, API keys).

        Return a dict with keys: success (bool), msg (optional str).
        """
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        """Perform the scheduled sync/work for this instance.

        Return a dict with status/metrics.
        """
        return {"success": True, "details": "noop"}

    def health(self) -> Dict[str, Any]:
        """Lightweight health check for the instance."""
        return {"status": "ok"}

    def blueprint(self) -> Optional[Blueprint]:
        """Optional: return a Flask Blueprint for plugin UI routes."""
        return None
