"""Scrapes TradingView for company logo images, keyed by PSE ticker
symbol. TradingView has no public API for this -- the logo URL is
extracted from a symbol page's og:image meta tag
(tradingview.com/symbols/PSE-{symbol}/), the same page-scraping approach
already used for PSE Edge throughout scraper/pse_edge.py. og:image is
always a PNG rendition (TradingView also exposes SVG logo variants
elsewhere on the page, but PNG needs no extra rasterization dependency to
work with this project's existing Pillow-based rendering). Downloading
the found URL reuses pse_edge.download_image/new_session rather than
duplicating a second HTTP client.
"""

import re

from scraper.pse_edge import new_session

BASE_URL = "https://www.tradingview.com"

OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="([^"]+)"')


def get_company_logo_url(symbol, session=None):
    """Returns the absolute URL of symbol's logo image (PNG, via the
    page's og:image meta tag), or None if the symbol has no TradingView
    page under this URL pattern, or the page has no such tag.
    """
    session = session or new_session()

    response = session.get(f"{BASE_URL}/symbols/PSE-{symbol}/")
    if response.status_code != 200:
        return None

    match = OG_IMAGE_RE.search(response.text)
    return match.group(1) if match else None
