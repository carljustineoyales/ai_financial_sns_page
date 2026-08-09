"""Local disk cache of company logo images, scraped from TradingView and
keyed by ticker symbol (PSE Edge's own /clogo/ images were the original
source; replaced with TradingView's, which cover more symbols).
rendering/primitives.py's _load_logo() only ever reads from LOGO_DIR and
never fetches -- it silently renders without a logo for any symbol not
yet cached. All network fetching happens in this module, and only when
run manually (`python assets_logos.py ...`); no poster or graphics module
calls ensure_logos() automatically anymore, so a cron run never triggers
an unattended download+decode of an externally-hosted image (see the
DecompressionBombWarning this surfaced during a manual
market_movers_poster.py test -- fetching/decoding arbitrary external
images shouldn't happen unattended in a scheduled pipeline).
"""

import argparse
import json
import os
import sys

from rendering.primitives import MAX_LOGO_SOURCE_PIXELS, _open_image_no_bomb_warning
from scraper import tradingview
from scraper.market_movers import COMPANY_DIRECTORY_CACHE, refresh_company_directory
from scraper.pse_edge import download_image

LOGO_DIR = os.path.join("assets", "logos")


def _load_company_directory():
    if os.path.exists(COMPANY_DIRECTORY_CACHE):
        with open(COMPANY_DIRECTORY_CACHE) as f:
            return json.load(f)
    return refresh_company_directory()


def get_logo_path(symbol):
    """Returns the local path to symbol's logo PNG, downloading and caching
    it on first use. Returns None (without creating a file, or removing one
    it just downloaded) if no logo could be found or downloaded, or if the
    downloaded image exceeds MAX_LOGO_SOURCE_PIXELS -- an oversized/
    corrupted file never lingers in the cache; callers fall back to
    text-only rendering.
    """
    dest_path = os.path.join(LOGO_DIR, f"{symbol}.png")
    if os.path.exists(dest_path):
        return dest_path

    try:
        logo_url = tradingview.get_company_logo_url(symbol)
        if not logo_url:
            return None

        os.makedirs(LOGO_DIR, exist_ok=True)
        download_image(logo_url, dest_path)

        with _open_image_no_bomb_warning(dest_path) as im:
            if im.width * im.height > MAX_LOGO_SOURCE_PIXELS:
                os.remove(dest_path)
                print(f"{symbol}: downloaded logo is {im.width}x{im.height}, over the size cap -- discarded.")
                return None

        return dest_path
    except Exception:
        return None


def ensure_logos(symbols):
    """Prefetches logos for every symbol (deduped), caching each to disk.
    Not called automatically by any poster/graphics module -- run manually
    (directly, or via `python assets_logos.py SYM1 SYM2 ...` / `--all`)
    whenever you want to backfill the cache before a pipeline run.
    """
    missing = []
    for symbol in sorted(set(symbols)):
        if not get_logo_path(symbol):
            missing.append(symbol)
    if missing:
        print(f"No logo found/downloaded for: {missing}")


def main():
    parser = argparse.ArgumentParser(
        description="Manually prefetch/cache company logos. Not run automatically by any pipeline script."
    )
    parser.add_argument("symbols", nargs="*", help="specific ticker symbols to fetch")
    parser.add_argument("--all", action="store_true", help="fetch every company in the PSE directory")
    args = parser.parse_args()

    if args.all:
        companies = _load_company_directory()
        symbols = [c["symbol"] for c in companies]
    elif args.symbols:
        symbols = args.symbols
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Fetching logos for {len(symbols)} symbol(s)...")
    ensure_logos(symbols)
    print("Done.")


if __name__ == "__main__":
    main()
