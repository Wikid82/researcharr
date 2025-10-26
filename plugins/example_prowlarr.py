from typing import Any, Dict

from flask import Blueprint, jsonify

from researcharr.plugins.base import BasePlugin

PLUGIN_NAME = "prowlarr"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "scrapers"
    description = "Example Prowlarr plugin (search indexer aggregator)"
    docs_url = "https://github.com/Prowlarr/Prowlarr"

    def validate(self) -> Dict[str, Any]:
        url = self.config.get("url")
        api_key = self.config.get("api_key")
        if not url or not api_key:
            return {"success": False, "msg": "Missing url or api_key"}
        return {"success": True}

    def sync(self) -> Dict[str, Any]:
        return {"success": True, "details": "prowlarr sync (noop)"}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self.config.get("name")}

    def blueprint(self):
        bp = Blueprint("prowlarr_plugin", __name__, url_prefix="/plugin/prowlarr")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "prowlarr", "config": self.config})

        return bp
