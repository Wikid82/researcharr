from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from plugins.base import BasePlugin

PLUGIN_NAME = "apprise"


class Plugin(BasePlugin):
    name = PLUGIN_NAME
    category = "notifications"
    description = "Apprise notification integration (uses 'apprise' package)"
    docs_url = "https://github.com/caronc/apprise"

    def _get_urls(self) -> List[str]:
        # Config may provide 'urls' (list) or 'url' (single string)
        urls = self.config.get("urls") or self.config.get("url")
        if isinstance(urls, str):
            return [urls]
        if isinstance(urls, list):
            return urls
        return []

    def validate(self) -> Dict[str, Any]:
        urls = self._get_urls()
        if not urls:
            return {
                "success": False,
                "msg": "No apprise URL(s) configured (set 'url' or 'urls').",
            }

        try:
            import apprise

            a = apprise.Apprise()
            added = 0
            for u in urls:
                try:
                    if a.add(u):
                        added += 1
                except Exception:
                    # skip problematic url
                    continue
            if added == 0:
                return {
                    "success": False,
                    "msg": "No valid apprise URLs could be added.",
                }
            return {"success": True, "added": added}
        except ImportError:
            return {"success": False, "msg": "apprise package not installed"}
        except Exception as exc:
            return {"success": False, "msg": f"validation error: {exc}"}

    def sync(self) -> Dict[str, Any]:
        """Send a test notification if 'test' is true in config or called via
        the blueprint.

        This method is conservative: it only sends if explicitly requested to
        avoid surprising users during routine syncs.
        """
        urls = self._get_urls()
        if not urls:
            return {"success": False, "msg": "No apprise URL(s) configured."}

        send_test = bool(self.config.get("test", False))
        if not send_test:
            return {"success": True, "details": "noop (test not requested)"}

        title = self.config.get("title", "ResearchArr Test Notification")
        body = self.config.get("body", "This is a test notification from ResearchArr.")

        try:
            import apprise

            a = apprise.Apprise()
            for u in urls:
                try:
                    a.add(u)
                except Exception:
                    continue

            ok = a.notify(body=body, title=title)
            return {"success": bool(ok)}
        except ImportError:
            return {"success": False, "msg": "apprise package not installed"}
        except Exception as exc:
            return {"success": False, "msg": f"send error: {exc}"}

    def health(self) -> Dict[str, Any]:
        # Lightweight health: same as validate but without raising on ImportError
        urls = self._get_urls()
        if not urls:
            return {"status": "error", "msg": "no urls configured"}
        try:
            import apprise

            a = apprise.Apprise()
            added = 0
            for u in urls:
                try:
                    if a.add(u):
                        added += 1
                except Exception:
                    continue
            return {"status": "ok" if added > 0 else "degraded", "added": added}
        except Exception:
            return {
                "status": "degraded",
                "msg": "apprise not available or error during check",
            }

    def blueprint(self):
        bp = Blueprint("apprise_plugin", __name__, url_prefix="/plugin/apprise")

        @bp.route("/info")
        def info():
            return jsonify({"plugin": "apprise", "config": self.config})

        @bp.route("/send", methods=["POST"])
        def send():
            payload = request.get_json(force=True, silent=True) or {}
            title = payload.get("title") or self.config.get("title") or "ResearchArr Notification"
            body = payload.get("body") or self.config.get("body") or ""
            # allow overriding urls for an explicit send
            urls = payload.get("urls") or self._get_urls()
            if not urls:
                return (
                    jsonify({"success": False, "msg": "no apprise urls configured"}),
                    400,
                )

            try:
                import apprise

                a = apprise.Apprise()
                for u in urls:
                    try:
                        a.add(u)
                    except Exception:
                        continue
                ok = a.notify(title=title, body=body)
                return jsonify({"success": bool(ok)})
            except Exception as exc:
                return jsonify({"success": False, "msg": str(exc)}), 500

        return bp


# Alias for test compatibility
ExampleApprisePlugin = Plugin
