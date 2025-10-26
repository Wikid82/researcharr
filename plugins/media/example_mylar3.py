from typing import Any, Dict

from flask import Blueprint, jsonify, request

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "mylar3"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Mylar3 integration (read/search)"
    docs_url = "https://github.com/mylar3/mylar3"

    def validate(self) -> Dict[str, Any]:
        if not self.config.get("url"):
            return {"success": False, "msg": "Missing url"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        if not self.config.get("url"):
            return {"success": True, "comics": []}
        try:
            import requests

            r = requests.get(f"{self.config.get('url')}/api?cmd=getAll&json=1", timeout=5)
            if r.status_code == 200:
                return {"success": True, "comics": r.json()}
        except Exception:
            pass
        return {"success": True, "comics": [{"id": 1, "title": "Example Comic"}]}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("mylar3_plugin", __name__, url_prefix="/plugin/mylar3")

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            comic_id = payload.get("id")
            if not comic_id:
                return jsonify({"success": False, "msg": "missing id"}), 400
            if not self.config.get("allow_remote_actions", False):
                return jsonify({"success": True, "msg": "simulated search (remote actions disabled)"})
            try:
                import requests

                r = requests.get(f"{self.config.get('url')}/api?cmd=search&comicid={comic_id}&json=1", timeout=10)
                return jsonify({"success": r.status_code == 200, "status_code": r.status_code})
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp
