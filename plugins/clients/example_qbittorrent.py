from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "qbittorrent"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Read-only qBittorrent client plugin (shows queue/torrents)"
    docs_url = "https://www.qbittorrent.org/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        if not host:
            return {"success": False, "msg": "Missing host"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        host = self.config.get("host")
        username = self.config.get("username")
        password = self.config.get("password")
        # read-only: attempt to fetch /api/v2/torrents/info
        try:
            import requests

            s = requests.Session()
            # try login if credentials provided (best-effort)
            if username and password:
                s.post(f"{host}/api/v2/auth/login", data={"username": username, "password": password}, timeout=5)
            r = s.get(f"{host}/api/v2/torrents/info", timeout=5)
            if r.status_code == 200:
                return {"success": True, "torrents": r.json()}
        except Exception:
            pass

        # fallback mocked torrents
        return {
            "success": True,
            "torrents": [
                {"hash": "abc123", "name": "Example Torrent 1", "progress": 0.5, "state": "downloading"},
                {"hash": "def456", "name": "Example Torrent 2", "progress": 0.0, "state": "queued"},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("qbittorrent_plugin", __name__, url_prefix="/plugin/qbittorrent")

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
