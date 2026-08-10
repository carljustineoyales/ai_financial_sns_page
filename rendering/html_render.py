"""Renders rendering/templates/*.html + _shared.css to PNG via headless
Chromium (Playwright). The templates are the source of truth for card
layout -- every render_*_card function in this package builds a Jinja2
context and hands it to render_card() rather than drawing with Pillow.
"""

import atexit
import os
import tempfile

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))

_playwright = None
_browser = None


def _get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch()
        atexit.register(_shutdown)
    return _browser


def _shutdown():
    global _playwright, _browser
    if _browser is not None:
        _browser.close()
        _playwright.stop()
        _browser = None
        _playwright = None


def render_card(template_name, context, output_path):
    """Renders rendering/templates/<template_name> with `context` via
    Jinja2, then screenshots the result's .card element (always exactly
    1080x1080, the fixed canvas every card template shares) to a PNG at
    output_path. The rendered HTML is written to a sibling temp file
    inside TEMPLATES_DIR (not a system tmp dir) so the template's
    relative asset paths (_shared.css, ../../assets/logos/*.png) resolve
    unchanged.
    """
    html = _env.get_template(template_name).render(**context)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".html", dir=TEMPLATES_DIR)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(html)

        page = _get_browser().new_page(viewport={"width": 1160, "height": 1160})
        try:
            page.goto(f"file://{tmp_path}")
            try:
                page.evaluate("document.fonts.ready")
            except Exception:
                pass  # webfont CDN unreachable -- CSS fallback stack (Inter/JetBrains Mono) still renders
            page.locator(".card").screenshot(path=output_path)
        finally:
            page.close()
    finally:
        os.remove(tmp_path)

    return output_path
