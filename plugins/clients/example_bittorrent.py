from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "bittorrent"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Generic BitTorrent read-only plugin (shows queue/torrents)"
    docs_url = "https://www.bittorrent.org/"

    def validate(self) -> Dict[str, Any]:
        # Generic plugin: no strict requirements
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # No standard API; return mocked data
        return {
            "success": True,
            "torrents": [
                {"id": "1", "name": "Example BT 1", "progress": 0.75},
                {"id": "2", "name": "Example BT 2", "progress": 0.0},
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def blueprint(self):
        bp = Blueprint("bittorrent_plugin", __name__, url_prefix="/plugin/bittorrent")

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
