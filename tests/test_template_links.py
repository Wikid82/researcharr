import os
import re
from pathlib import Path


def _find_template_links(template_dir: Path):
    links = set()
    href_re = re.compile(r"href=\"(/[^\"#? ]*)")
    action_re = re.compile(r"action=\"(/[^\"#? ]*)")
    for p in template_dir.rglob("*.html"):
        text = p.read_text(encoding="utf-8")
        for m in href_re.finditer(text):
            links.add(m.group(1))
        for m in action_re.finditer(text):
            links.add(m.group(1))
    return sorted(links)


def _find_app_routes(factory_path: Path):
    text = factory_path.read_text(encoding="utf-8")
    routes = set()
    # Simple capture of @app.route('/path') and @app.route("/path")
    for m in re.finditer(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", text):
        routes.add(m.group(1))
    # Find registered blueprints with url_prefix
    for m in re.finditer(
        r"register_blueprint\([^,]+,\s*url_prefix=\s*['\"]([^'\"]+)['\"]", text
    ):
        routes.add(m.group(1).rstrip("/"))
    return routes


def _is_covered(link: str, routes: set):
    # Ignore external links, static assets, anchors
    if link.startswith("/static/"):
        return True
    if link.startswith("http://") or link.startswith("https://"):
        return True
    # Exact match
    if link in routes:
        return True
    # Parameterized route match e.g. /foo/<int:id> should cover /foo/bar
    for r in routes:
        # strip trailing slash for comparison
        if r.endswith("/"):
            r = r.rstrip("/")
        if r == "":
            continue
        if link == r:
            return True
        # if route contains < treat as prefix
        if "<" in r:
            prefix = r.split("/<")[0]
            if link.startswith(prefix):
                return True
        # if route is a prefix (blueprint base)
        if link.startswith(r + "/"):
            return True
    return False


def test_templates_have_matching_routes():
    repo_root = Path(__file__).resolve().parents[1]
    template_dir = repo_root / "templates"
    factory_path = repo_root / "factory.py"
    assert template_dir.exists(), f"templates directory missing: {template_dir}"
    assert factory_path.exists(), f"factory.py missing: {factory_path}"

    links = _find_template_links(template_dir)
    routes = _find_app_routes(factory_path)

    missing = []
    for l in links:
        if not _is_covered(l, routes):
            missing.append(l)

    assert (
        not missing
    ), f"Found template links with no matching route/blueprint: {missing}"
