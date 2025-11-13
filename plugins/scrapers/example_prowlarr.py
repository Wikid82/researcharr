from typing import Any

from flask import Blueprint, jsonify
from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "prowlarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "scrapers"
    description = "Example Prowlarr plugin (search indexer aggregator)"
    docs_url = "https://github.com/Prowlarr/Prowlarr"

    def validate(self) -> dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> dict[str, Any]:
        # Read-only: attempt to fetch indexer/status information from Prowlarr
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": True, "indexers": []}

        try:
            import requests

            r = requests.get(f"{url}/api/v1/status?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"success": True, "indexers": r.json()}
            # fallback to list indexers
            r2 = requests.get(f"{url}/api/v1/indexer?apikey={api_key}", timeout=5)
            if r2.status_code == 200:
                return {"success": True, "indexers": r2.json()}
        except Exception:
            pass

        # Fallback mocked indexers
        return {
            "success": True,
            "indexers": [
                {"id": "1", "name": "Example Indexer 1", "enabled": True},
                {"id": "2", "name": "Example Indexer 2", "enabled": False},
            ],
        }

    def health(self) -> dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"status": "degraded", "msg": "not configured"}
        try:
            import requests

            r = requests.get(f"{url}/api/v1/status?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"status": "ok"}
        except Exception:
            pass
        return {"status": "degraded"}

    def blueprint(self):
        bp = Blueprint("prowlarr_plugin", __name__, url_prefix="/plugin/prowlarr")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "prowlarr", "config": self.config})

        @bp.route("/indexers")
        def indexers():
            return jsonify(self.sync())

        return bp
