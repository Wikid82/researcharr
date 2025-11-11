from typing import Any

from flask import Blueprint, jsonify, request
from plugins.base import BasePlugin

PLUGIN_NAME = "radarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Example Radarr plugin (test harness)"
    docs_url = "https://radarr.video/"

    def validate(self) -> dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> dict[str, Any]:
        # Read-only: fetch movies list from Radarr to reflect DB state for processing
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": True, "movies": []}

        try:
            import requests

            # Radarr commonly exposes /api/v3/movie
            r = requests.get(f"{url}/api/v3/movie?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"success": True, "movies": r.json()}
        except Exception:
            pass

        # Fallback mocked movie list
        return {
            "success": True,
            "movies": [
                {
                    "id": 1,
                    "title": "Example Movie 1",
                    "year": 2020,
                    "status": "released",
                },
                {"id": 2, "title": "Example Movie 2", "year": 2023, "status": "wanted"},
            ],
        }

    def health(self) -> dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"status": "degraded", "msg": "not configured"}
        try:
            import requests

            r = requests.get(f"{url}/api/v3/system/status?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"status": "ok"}
        except Exception:
            pass
        return {"status": "degraded"}

    def blueprint(self):
        bp = Blueprint("radarr_plugin", __name__, url_prefix="/plugin/radarr")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "radarr", "config": self.config})

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            movie_id = payload.get("id")
            if not movie_id:
                return jsonify({"success": False, "msg": "missing id"}), 400

            # Only perform remote actions if explicitly allowed in config
            if not self.config.get("allow_remote_actions", False):
                return jsonify(
                    {
                        "success": True,
                        "msg": "simulated search (remote actions disabled)",
                    }
                )

            url = self.config.get("url")
            api_key = self.config.get("api_key")
            try:
                import requests

                # Radarr supports POST /api/v3/movie/{id}/search
                r = requests.post(
                    f"{url}/api/v3/movie/{movie_id}/search?apikey={api_key}", timeout=10
                )
                return jsonify(
                    {
                        "success": r.status_code == 200,
                        "status_code": r.status_code,
                        "text": r.text,
                    }
                )
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp
