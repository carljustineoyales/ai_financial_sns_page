"""Shared helpers used by every card renderer in this package: logo
decoding (_open_image_no_bomb_warning, MAX_LOGO_SOURCE_PIXELS, used by
assets_logos.py too) and the small set of context-building utilities
every HTML/Playwright renderer (see html_render.py) uses --
_logo_src/_company_name/_estimate_footer_line_count.
"""

import json
import os
import warnings

from PIL import Image

from .theme import ASSETS_LOGO_DIR, COMPANY_DIRECTORY_CACHE

# Generous for an icon-sized company logo (2000x2000), well under Pillow's
# own 89M-pixel DecompressionBombWarning threshold. Pillow fires its own
# warning as a side effect of Image.open() itself (as soon as it reads the
# file's declared dimensions from the header), before any code here gets a
# chance to compare against this cap -- so opening has to happen inside a
# warnings suppression block, not just be followed by a size check.
MAX_LOGO_SOURCE_PIXELS = 4_000_000


def _open_image_no_bomb_warning(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return Image.open(path)


def _estimate_footer_line_count(text, width_px, font_px=15, avg_char_width_ratio=0.52):
    """Rough line count for wrapped footer text at width_px, used only to
    budget how many rows/items a variable-length card body can show
    before it'd push the footer past the fixed 1080px canvas -- the
    browser does the actual wrapping (see rendering/templates/_shared.css
    .footer-text), so this only needs to be a reasonable estimate, not
    pixel-exact.
    """
    chars_per_line = max(1, int(width_px / (font_px * avg_char_width_ratio)))
    return max(1, -(-len(text) // chars_per_line))


def _logo_src(symbol):
    """Path to symbol's cached logo, relative to a rendered template's
    temp file location (rendering/templates/<tmpfile>.html), or None if
    no logo is cached -- callers' templates fall back to plain
    ticker/symbol text in that case.
    """
    path = os.path.join(ASSETS_LOGO_DIR, f"{symbol}.png")
    if not os.path.exists(path):
        return None
    return os.path.join("..", "..", path)


_company_name_cache = None


def _company_name(symbol):
    """Full company name for a ticker symbol, from the cached PSE company
    directory (see scraper/market_movers.py, which maintains this cache).
    Falls back to the symbol itself if the cache is missing or the symbol
    isn't found in it.
    """
    global _company_name_cache
    if _company_name_cache is None:
        _company_name_cache = {}
        if os.path.exists(COMPANY_DIRECTORY_CACHE):
            with open(COMPANY_DIRECTORY_CACHE) as f:
                companies = json.load(f)
            _company_name_cache = {c["symbol"]: c["company"] for c in companies}

    return _company_name_cache.get(symbol, symbol)
