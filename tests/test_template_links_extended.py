import re
from pathlib import Path


def test_templates_fetch_and_links_covered():
    repo_root = Path(__file__).resolve().parents[1]
    template_dir = repo_root / "templates"
    factory_path = repo_root / "factory.py"

    assert template_dir.exists()
    assert factory_path.exists()

    text = ""
    for p in template_dir.rglob("*.html"):
        text += p.read_text(encoding="utf-8") + "\n"

    # find fetch('/path') or fetch("/path") occurrences
    fetch_re = re.compile(r"fetch\(\s*['\"](/[^'\")]+)")
    # strip query params (e.g. /api/tasks?limit=) so we only compare paths
    fetch_links = set(m.group(1).split("?", 1)[0] for m in fetch_re.finditer(text))

    # reuse existing template link test's route discovery logic
    factory_text = factory_path.read_text(encoding="utf-8")
    routes = set()
    for m in re.finditer(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", factory_text):
        routes.add(m.group(1))
    for m in re.finditer(
        r"register_blueprint\([^,]+,\s*url_prefix=\s*['\"]([^'\"]+)['\"]", factory_text
    ):
        routes.add(m.group(1).rstrip("/"))

    def covered(link):
        if link.startswith("/static/"):
            return True
        if link in routes:
            return True
        for r in routes:
            if "<" in r:
                prefix = r.split("/<")[0]
                if link.startswith(prefix):
                    return True
            if link.startswith(r + "/"):
                return True
        return False

    missing = [link for link in fetch_links if not covered(link)]
    assert (
        not missing
    ), f"Found fetch() links with no matching route/blueprint: {missing}"
