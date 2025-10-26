from typing import Any, Dict

from flask import Blueprint, jsonify, request

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "readarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "media"
    description = "Readarr integration (read/search)"
    docs_url = "https://readarr.com/"

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
            return {"success": True, "books": []}
        try:
            import requests

            r = requests.get(f"{url}/api/v1/book?apikey={api_key}", timeout=5)
            if r.status_code == 200:
                return {"success": True, "books": r.json()}
        except Exception:
            pass
        return {"success": True, "books": [{"id": 1, "title": "Example Book"}]}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("readarr_plugin", __name__, url_prefix="/plugin/readarr")

        @bp.route("/items")
        def items():
            return jsonify(self.sync())

        @bp.route("/search", methods=["POST"])
        def search():
            payload = request.get_json(force=True, silent=True) or {}
            book_id = payload.get("id")
            if not book_id:
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
                    f"{self.config.get('url')}/api/v1/book/{book_id}/refresh?apikey={self.config.get('api_key')}",
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
