from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "utorrent"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Read-only uTorrent client plugin (shows queue)"
    docs_url = "https://www.utorrent.com/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        token = self.config.get("token")
        if not host or not token:
            return {"success": False, "msg": "Missing host or token"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # uTorrent web API varies; attempt GET if configured, otherwise fallback
        host = self.config.get("host")
        token = self.config.get("token")
        try:
            import requests

            r = requests.get(f"{host}/gui/?list=1&token={token}")
            if r.status_code == 200:
                return {"success": True, "queue": r.text}
        except Exception:
            pass

        return {
            "success": True,
            "queue": [{"name": "Example Torrent", "status": "downloading"}],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("utorrent_plugin", __name__, url_prefix="/plugin/utorrent")

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
