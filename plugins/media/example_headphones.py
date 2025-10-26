from typing import Any, Dict

from flask import Blueprint, jsonify, request

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "headphones"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Headphones integration (read/search)"
    docs_url = "https://github.com/rembo10/headphones"

    def validate(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        if not self.config.get("url"):
            return {"success": True, "albums": []}
        try:
            import requests

            r = requests.get(
                f"{self.config.get('url')}/api/artist.get?apikey={self.config.get('api_key')}",
                timeout=5,
            )
            if r.status_code == 200:
                return {"success": True, "albums": r.json()}
        except Exception:
            pass
        return {"success": True, "albums": [{"id": 1, "title": "Example Album"}]}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("headphones_plugin", __name__, url_prefix="/plugin/headphones")

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            album_id = payload.get("id")
            if not album_id:
                return jsonify({"success": False, "msg": "missing id"}), 400
            if not self.config.get("allow_remote_actions", False):
                return jsonify(
                    {
                        "success": True,
                        "msg": "simulated search (remote actions disabled)",
                    }
                )
            try:
                import requests

                r = requests.post(
                    f"{self.config.get('url')}/api/album/{album_id}/refresh?apikey={self.config.get('api_key')}",
                    timeout=10,
                )
                return jsonify(
                    {
                        "success": r.status_code in (200, 201),
                        "status_code": r.status_code,
                    }
                )
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp
