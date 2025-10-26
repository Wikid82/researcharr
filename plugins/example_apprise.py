from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "apprise"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "notifications"
    description = "Apprise notifications (example integration)"
    docs_url = "https://github.com/caronc/apprise"

    def validate(self) -> Dict[str, Any]:
        # For tests this is a noop; real integration would attempt to send
        # a test notification using the provided service URL/token.
        service = self.config.get("service")
        if not service:
            return {"success": False, "msg": "Missing service/target"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        # Nothing to sync for notification providers
        return {"success": True, "details": "apprise noop"}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self.config.get("name")}

    def blueprint(self):
        bp = Blueprint("apprise_plugin", __name__, url_prefix="/plugin/apprise")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "apprise", "config": self.config})

        return bp
