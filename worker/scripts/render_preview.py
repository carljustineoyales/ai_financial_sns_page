"""Renders the graphic cards to PNG without posting anywhere.

Reuses the real scraping/watchlist logic from dividend_graphics.py, which
has no dependency on posters.facebook (post_photo/post_to_page) at all.

Usage:
    python scripts/render_preview.py calendar   # next month's dividend calendar card
    python scripts/render_preview.py year       # full year overview + month detail cards
    python scripts/render_preview.py both       # both (default)
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from dividend_tracker import _symbol_lookup, get_watchlist_symbols
from logging_config import setup_logging
from scraper.pse_edge import get_dividends_and_rights

PREVIEW_DIR = os.path.join("output", "_preview")

logger = logging.getLogger(__name__)


def render_calendar():
    from dividend_graphics import build_month_card as build_card, get_month_dividend_events, get_next_month

    year, month = get_next_month()
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    logger.info("Fetching dividend declarations from PSE Edge for %s-%02d...", year, month)
    entries = get_dividends_and_rights()
    events = get_month_dividend_events(entries, watchlist, symbol_lookup, year, month)
    logger.info("%d watchlist dividend events for %s-%02d.", len(events), year, month)

    if not events:
        logger.info("Nothing scheduled in this window -- nothing to render.")
        return

    os.makedirs(PREVIEW_DIR, exist_ok=True)
    output_path = os.path.join(PREVIEW_DIR, f"calendar-{year}-{month:02d}.png")
    build_card(events, year, month, output_path)
    logger.info("Saved %s", output_path)


def render_year():
    from dividend_graphics import build_year_card as build_card, build_month_detail_cards, get_current_year_by_month
    from datetime import date

    year = date.today().year
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    logger.info("Fetching dividend declarations from PSE Edge...")
    entries = get_dividends_and_rights()
    months_data = get_current_year_by_month(entries, watchlist, symbol_lookup, year=year)
    for month in range(1, 13):
        logger.info("  %02d: %d tickers", month, len(months_data[month]))

    output_dir = os.path.join(PREVIEW_DIR, "year_overview", str(year))
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "overview.png")
    build_card(months_data, year, image_path)
    logger.info("Saved %s", image_path)

    detail_paths = build_month_detail_cards(months_data, year, output_dir)
    for path in detail_paths:
        logger.info("Saved %s", path)


def main():
    setup_logging()
    load_dotenv()
    target = sys.argv[1] if len(sys.argv) > 1 else "both"

    if target in ("calendar", "both"):
        render_calendar()
    if target in ("year", "both"):
        render_year()


if __name__ == "__main__":
    main()
