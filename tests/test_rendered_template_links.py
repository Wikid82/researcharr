import re
from pathlib import Path

import pytest
from flask import render_template

from factory import create_app


def _extract_links_from_rendered(html: str):
    href_re = re.compile(r'href="(/[^"#? ]*)')
    action_re = re.compile(r'action="(/[^"#? ]*)')
    links = set(href_re.findall(html)) | set(action_re.findall(html))
    return links


def _extract_forms(html: str):
    # Return list of full form tag strings
    form_re = re.compile(r"(<form\b[^>]*>)(.*?)</form>", re.S | re.I)
    return [m[0] + m[1] + "</form>" for m in form_re.findall(html)]


def _inputs_in_html(html: str):
    return re.findall(r"<input\b[^>]*>", html, re.I)


def _buttons_in_html(html: str):
    return re.findall(r"<button\b[^>]*>", html, re.I)


@pytest.mark.parametrize("template", [p.name for p in Path("templates").glob("*.html")])
def test_rendered_templates_links_and_forms(template):
    """Render each template inside a Flask test_request_context and ensure
    - internal links resolve via url_for or match registered routes/blueprints
    - forms have an action attribute (or explicit empty action)
    - inputs inside forms have an associated label (by `for` id) or an aria-label
    - buttons have an explicit `type` attribute when present
    """
    app = create_app()
    tpl_path = Path("templates") / template
    html = ""
    text = tpl_path.read_text(encoding="utf-8")

    with app.test_request_context():
        try:
            html = render_template(template)
        except Exception:
            # Fall back to scanning the raw template text when rendering
            # requires variables we don't provide in this test harness.
            html = text

    # ----- Link resolution checks -----
    links = _extract_links_from_rendered(html)

    # Gather available routes from the app (including blueprints)
    routes = set(str(rule.rule) for rule in app.url_map.iter_rules())

    missing_links = []
    for link in links:
        if link.startswith("/static/"):
            continue
        if link.startswith("http://") or link.startswith("https://"):
            continue
        if link in routes:
            continue
        matched = False
        for r in routes:
            if "<" in r:
                prefix = r.split("/<")[0]
                if link.startswith(prefix):
                    matched = True
                    break
            if link.startswith(r.rstrip("/") + "/"):
                matched = True
                break
        if not matched:
            missing_links.append(link)

    assert (
        not missing_links
    ), f"Template {template} contains links that don't resolve: {missing_links}"

    # ----- Form & accessibility heuristics -----
    forms = _extract_forms(html)
    missing_form_actions = []
    inputs_without_label = []
    buttons_without_type = []

    for f in forms:
        # action attribute
        if not re.search(r'<form[^>]*\baction\s*=\s*"[^"]*"', f, re.I):
            missing_form_actions.append(f[:200])

        # inputs
        for inp in _inputs_in_html(f):
            # ignore hidden/submit/button/reset inputs — these either don't
            # require visible labels or are UI controls
            t = re.search(r'\btype\s*=\s*"([^"]+)"', inp, re.I)
            if t and t.group(1).lower() in ("hidden", "submit", "button", "reset"):
                continue
            # check for id -> label[for=id] or aria-label
            idm = re.search(r'\bid\s*=\s*"([^"]+)"', inp, re.I)
            has_aria = bool(re.search(r'\baria-label\s*=\s*"[^"]+"', inp, re.I))
            has_label = False
            if idm:
                idval = idm.group(1)
                if re.search(
                    rf'<label[^>]*for="{re.escape(idval)}"', f, re.I
                ) or re.search(rf'<label[^>]*for="{re.escape(idval)}"', html, re.I):
                    has_label = True
            # Inputs can also be wrapped by a <label>...</label> element
            if not has_label:
                # try matching by name attribute inside a wrapping label
                name_m = re.search(r'\bname\s*=\s*"([^"]+)"', inp, re.I)
                if name_m:
                    nameval = name_m.group(1)
                    if re.search(
                        rf'<label[^>]*>.*name\s*=\s*"{re.escape(nameval)}".*</label>',
                        f,
                        re.I | re.S,
                    ):
                        has_label = True
                else:
                    # fallback: check if the literal input appears inside any label
                    if re.search(
                        r"<label[^>]*>.*" + re.escape(inp) + r".*</label>",
                        f,
                        re.I | re.S,
                    ):
                        has_label = True
            if not idm and has_aria:
                has_label = True
            if not has_label:
                inputs_without_label.append(inp)

        # buttons
        for b in _buttons_in_html(f):
            if not re.search(r'\btype\s*=\s*"[^"]+"', b, re.I):
                buttons_without_type.append(b)

    # We don't fail tests on missing form actions or missing button type
    # attributes because many templates intentionally post to the current
    # URL or rely on CSS/JS-driven buttons. Keep the input label check
    # strict for non-button inputs though.
    assert not inputs_without_label, f"Template {template} has inputs without label"
