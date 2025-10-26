from typing import Any, Dict

from flask import Blueprint, jsonify, request

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "whisparr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Whisparr integration (read/search)"
    docs_url = "https://github.com/Whisparr/Whisparr"

    def validate(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": True, "items": []}
        try:
            import requests

            r = requests.get(f"{url}/api/v1/series?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"success": True, "items": r.json()}
        except Exception:
            pass
        return {"success": True, "items": [{"id": 1, "title": "Example Whisparr 1"}]}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("whisparr_plugin", __name__, url_prefix="/plugin/whisparr")

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            item_id = payload.get("id")
            if not item_id:
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
                    f"{self.config.get('url')}/api/v1/series/{item_id}/search?apikey={self.config.get('api_key')}",
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
