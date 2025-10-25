from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "sonarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME

    def validate(self) -> Dict[str, Any]:
        # Very small placeholder validation
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Never actually call external services in this example
        return {"success": True, "details": "synced (noop)"}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self.config.get("name")}

    def blueprint(self):
        bp = Blueprint("sonarr_plugin", __name__, url_prefix="/plugin/sonarr")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "sonarr", "config": self.config})

        return bp
