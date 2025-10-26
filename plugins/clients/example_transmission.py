from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "transmission"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Read-only Transmission client plugin (shows queue/torrents)"
    docs_url = "https://transmissionbt.com/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        if not host:
            return {"success": False, "msg": "Missing host"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Attempt to query Transmission RPC if configured
        host = self.config.get("host")
        try:
            import json

            import requests

            # Transmission RPC expects POST with JSON body
            payload = {
                "method": "torrent-get",
                "arguments": {"fields": ["id", "name", "percentDone", "status"]},
            }
            r = requests.post(host, json=payload, timeout=5)
            if r.status_code == 200:
                return {"success": True, "data": r.json().get("arguments", {})}
        except Exception:
            pass

        return {
            "success": True,
            "torrents": [
                {"id": 1, "name": "Example Transmission 1", "progress": 0.33},
                {"id": 2, "name": "Example Transmission 2", "progress": 1.0},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint(
            "transmission_plugin", __name__, url_prefix="/plugin/transmission"
        )

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
