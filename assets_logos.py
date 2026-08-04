"""Local disk cache of company logo images, scraped from PSE Edge and keyed
by ticker symbol. renderer.py only ever reads from LOGO_DIR -- all network
fetching happens here so poster scripts can prefetch before rendering.
"""

import json
import os

from scraper import pse_edge
from scraper.market_movers import COMPANY_DIRECTORY_CACHE, refresh_company_directory

LOGO_DIR = os.path.join("assets", "logos")


def _load_company_directory():
    if os.path.exists(COMPANY_DIRECTORY_CACHE):
        with open(COMPANY_DIRECTORY_CACHE) as f:
            return json.load(f)
    return refresh_company_directory()


def _cmpy_id_for_symbol(symbol):
    for company in _load_company_directory():
        if company["symbol"] == symbol and company.get("cmpy_id"):
            return company["cmpy_id"]
    return None


def get_logo_path(symbol):
    """Returns the local path to symbol's logo PNG, downloading and caching
    it on first use. Returns None (without creating a file) if no logo could
    be found or downloaded, so callers can fall back to text-only rendering.
    """
    dest_path = os.path.join(LOGO_DIR, f"{symbol}.png")
    if os.path.exists(dest_path):
        return dest_path

    cmpy_id = _cmpy_id_for_symbol(symbol)
    if not cmpy_id:
        return None

    try:
        logo_url = pse_edge.get_company_logo_url(cmpy_id)
        if not logo_url:
            return None

        os.makedirs(LOGO_DIR, exist_ok=True)
        pse_edge.download_image(logo_url, dest_path)
        return dest_path
    except Exception:
        return None


def ensure_logos(symbols):
    """Prefetches logos for every symbol (deduped), caching each to disk.
    Call this before rendering so renderer.py never needs to hit the network.
    """
    for symbol in sorted(set(symbols)):
        get_logo_path(symbol)
