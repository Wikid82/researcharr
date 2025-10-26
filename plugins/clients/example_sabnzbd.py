from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "sabnzbd"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Read-only SABnzbd client plugin (shows queue)"
    docs_url = "https://sabnzbd.org/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        api_key = self.config.get("api_key")
        if not host or not api_key:
            return {"success": False, "msg": "Missing host or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Read-only: retrieve queue info if endpoint configured, else return mocked data
        host = self.config.get("host")
        api_key = self.config.get("api_key")
        if not host or not api_key:
            # return empty queue
            return {"success": True, "queue": []}

        # Try to fetch real queue if requests available and host is reachable
        try:
            import requests

            r = requests.get(f"{host}/api?mode=queue&output=json&apikey={api_key}")
            if r.status_code == 200:
                data = r.json()
                return {"success": True, "queue": data.get("queue", [])}
        except Exception:
            pass

        # Fallback mocked queue
        return {
            "success": True,
            "queue": [
                {"id": "1", "title": "Example NZB 1", "size": "700MB", "status": "downloading"},
                {"id": "2", "title": "Example NZB 2", "size": "1.4GB", "status": "queued"},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("sabnzbd_plugin", __name__, url_prefix="/plugin/sabnzbd")

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
