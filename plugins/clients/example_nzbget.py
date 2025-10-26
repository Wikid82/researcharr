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
        # Read-only: attempt to fetch queue info from NZBGet if configured,
        # otherwise return a mocked queue for UI display.
        host = self.config.get("host")
        port = self.config.get("port")
        if not host or not port:
            return {"success": True, "queue": []}

        base = host if host.startswith("http") else f"http://{host}:{port}"
        try:
            import requests

            # Try JSON-RPC endpoint first (common for NZBGet)
            try:
                payload = {"method": "listgroups", "params": []}
                r = requests.post(f"{base}/jsonrpc", json=payload, timeout=5)
                if r.status_code == 200:
                    j = r.json()
                    groups = j.get("result") if isinstance(j, dict) else j
                    return {"success": True, "queue": groups}
            except Exception:
                pass

            # Try a more generic API path
            try:
                r = requests.get(f"{base}/api?mode=queue&output=json", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return {"success": True, "queue": data.get("queue", data)}
            except Exception:
                pass
        except Exception:
            # requests not available or network error; fall through to mocked
            pass

        # Fallback mocked queue
        return {
            "success": True,
            "queue": [
                {
                    "id": "1",
                    "title": "Example NZB 1",
                    "size": "700MB",
                    "status": "downloading",
                },
                {
                    "id": "2",
                    "title": "Example NZB 2",
                    "size": "1.4GB",
                    "status": "queued",
                },
            ],
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self.config.get("name")}

    def blueprint(self):
        bp = Blueprint("nzbget_plugin", __name__, url_prefix="/plugin/nzbget")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "nzbget", "config": self.config})

        @bp.route("/queue")
        def queue():
            return jsonify(self.sync())

        return bp
