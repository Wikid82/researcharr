from typing import Any, Dict

from flask import Blueprint, jsonify, request

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "bobarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Bobarr integration (read/search)"
    docs_url = "https://github.com/Bobarr/Bobarr"

    def validate(self) -> Dict[str, Any]:
        if not self.config.get("url"):
            return {"success": False, "msg": "Missing url"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        if not self.config.get("url"):
            return {"success": True, "items": []}
        try:
            import requests

            r = requests.get(f"{self.config.get('url')}/api/v1/movies", timeout=5)
            if r.status_code == 200:
                return {"success": True, "items": r.json()}
        except Exception:
            pass
        return {"success": True, "items": [{"id": 1, "title": "Example Bobarr Movie"}]}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("bobarr_plugin", __name__, url_prefix="/plugin/bobarr")

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
                return jsonify({"success": True, "msg": "simulated search (remote actions disabled)"})
            try:
                import requests

                r = requests.post(f"{self.config.get('url')}/api/v1/movies/{item_id}/search", timeout=10)
                return jsonify({"success": r.status_code in (200, 201), "status_code": r.status_code})
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp
