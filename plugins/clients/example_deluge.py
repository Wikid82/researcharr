from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "deluge"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Read-only Deluge client plugin (shows queue/torrents)"
    docs_url = "https://deluge-torrent.org/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        if not host:
            return {"success": False, "msg": "Missing host"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Try Deluge Web API if available
        host = self.config.get("host")
        try:
            import requests

            r = requests.get(f"{host}/json")
            if r.status_code == 200:
                return {"success": True, "data": r.json()}
        except Exception:
            pass

        # Fallback mocked torrents
        return {
            "success": True,
            "torrents": [
                {"id": "1", "name": "Example Deluge 1", "progress": 0.2},
                {"id": "2", "name": "Example Deluge 2", "progress": 1.0},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("deluge_plugin", __name__, url_prefix="/plugin/deluge")

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
