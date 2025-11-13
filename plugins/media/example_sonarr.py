from typing import Any

from flask import Blueprint, jsonify, request
from plugins.base import BasePlugin

PLUGIN_NAME = "sonarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Example Sonarr plugin (read/search test harness)"
    docs_url = "https://sonarr.video/"

    def validate(self) -> dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> dict[str, Any]:
        # Read-only: fetch series list from Sonarr
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": True, "series": []}

        try:
            import requests

            r = requests.get(f"{url}/api/v3/series?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"success": True, "series": r.json()}
        except Exception:
            pass

        return {
            "success": True,
            "series": [
                {"id": 1, "title": "Example Series 1", "seasons": 3},
                {"id": 2, "title": "Example Series 2", "seasons": 1},
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
        bp = Blueprint("sonarr_plugin", __name__, url_prefix="/plugin/sonarr")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "sonarr", "config": self.config})

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            # payload can contain seriesId, season, episode for flexible searches
            series_id = payload.get("seriesId") or payload.get("id")
            # season is not used directly in this example; keep payload parsing flexible
            episode = payload.get("episode")

            if not series_id:
                return jsonify({"success": False, "msg": "missing seriesId"}), 400

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

                # Try episode-level search first
                if episode is not None:
                    r = requests.post(
                        f"{url}/api/v3/episode/{episode}/search?apikey={api_key}",
                        timeout=10,
                    )
                    return jsonify(
                        {
                            "success": r.status_code == 200,
                            "status_code": r.status_code,
                            "text": r.text,
                        }
                    )

                # Otherwise, try series-level command
                payload_cmd = {"name": "SeriesSearch", "seriesId": series_id}
                r = requests.post(
                    f"{url}/api/v3/command?apikey={api_key}",
                    json=payload_cmd,
                    timeout=10,
                )
                return jsonify(
                    {
                        "success": r.status_code in (200, 201),
                        "status_code": r.status_code,
                        "text": r.text,
                    }
                )
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp


# Alias for test compatibility
ExampleSonarrPlugin = Plugin
