from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "nzbget"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "clients"
    description = "Example NZBGet client plugin"
    docs_url = "https://nzbget.net/"

    def validate(self) -> Dict[str, Any]:
        host = self.config.get("host")
        port = self.config.get("port")
        if not host or not port:
            return {"success": False, "msg": "Missing host or port"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        return {"success": True, "details": "nzbget sync (noop)"}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self.config.get("name")}

    def blueprint(self):
        bp = Blueprint("nzbget_plugin", __name__, url_prefix="/plugin/nzbget")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "nzbget", "config": self.config})

        return bp
