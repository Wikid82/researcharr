from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "jackett"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "scrapers"
    description = "Read-only Jackett plugin (shows indexers and status)"
    docs_url = "https://github.com/Jackett/Jackett"

    def validate(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Read-only: attempt to fetch indexers/status
        # from Jackett (different API paths per version)
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": True, "indexers": []}

        try:
            import requests

            # Try the two common Jackett indexer endpoints
            endpoints = ["/api/v2.0/indexers", "/api/v2/indexers"]
            for ep in endpoints:
                try:
                    ep_url = f"{url}{ep}"
                    r = requests.get(f"{ep_url}?apikey={api_key}", timeout=5)
                    if r.status_code == 200:
                        return {"success": True, "indexers": r.json()}
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback mocked indexers
        return {
            "success": True,
            "indexers": [
                {"id": "1", "name": "Example Jackett 1", "enabled": True},
                {"id": "2", "name": "Example Jackett 2", "enabled": False},
            ],
        }

    def health(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"status": "degraded", "msg": "not configured"}
        try:
            import requests

            base = url
            key = api_key

            r = requests.get(f"{base}/api/v2.0/indexers?apikey={key}", timeout=5)
            if r.status_code == 200:
                return {"status": "ok"}
        except Exception:
            pass
        return {"status": "degraded"}

    def blueprint(self):
        bp = Blueprint("jackett_plugin", __name__, url_prefix="/plugin/jackett")

        @bp.route("/indexers")
        def indexers():
            return jsonify(self.sync())

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "jackett", "config": self.config})

        return bp
