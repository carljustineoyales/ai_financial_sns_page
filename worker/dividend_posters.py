"""Posts PSE dividend graphics to the configured Facebook Page: a
next-month dividend ex-date calendar card ("month") and a full-year
(Jan-Dec) dividend payout overview card plus per-month detail cards
("year"). Graphic generation lives in dividend_graphics.py; this module
handles data-fetch orchestration, preview/confirm, and posting.
"""

import argparse
import logging
import os
from datetime import date

from dotenv import load_dotenv

import dividend_graphics as graphics
from dividend_tracker import _symbol_lookup, get_watchlist_symbols
from logging_config import setup_logging
from posters.preview_and_post import preview_and_post
from scraper.pse_edge import get_dividends_and_rights

logger = logging.getLogger(__name__)


def main_month():
    year, month = graphics.get_next_month()
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    logger.info("Fetching dividend declarations from PSE Edge for %s-%02d...", year, month)
    entries = get_dividends_and_rights()

    events = graphics.get_month_dividend_events(entries, watchlist, symbol_lookup, year, month)
    logger.info("%d watchlist dividend events for %s-%02d.", len(events), year, month)

    if not events:
        logger.info("Nothing scheduled in this window -- skipping post.")
        return

    os.makedirs(graphics.MONTH_OUTPUT_DIR, exist_ok=True)
    image_name = f"{year}-{month:02d}"
    image_path = os.path.join(graphics.MONTH_OUTPUT_DIR, f"{image_name}.png")
    graphics.build_month_card(events, year, month, image_path)
    logger.info("Saved card to %s", image_path)

    caption = graphics.build_month_caption()
    record_path = os.path.join(graphics.MONTH_OUTPUT_DIR, f"{image_name}.json")
    preview_and_post(image_path, caption, record_path)


def main_year():
    year = date.today().year
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    logger.info("Fetching dividend declarations from PSE Edge...")
    entries = get_dividends_and_rights()

    months_data = graphics.get_current_year_by_month(entries, watchlist, symbol_lookup, year=year)
    for month in range(1, 13):
        logger.info("  %02d: %d tickers", month, len(months_data[month]))

    output_dir = graphics.year_output_dir(year)
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "overview.png")
    graphics.build_year_card(months_data, year, image_path)
    logger.info("Saved card to %s", image_path)

    detail_paths = graphics.build_month_detail_cards(months_data, year, output_dir)
    for path in detail_paths:
        logger.info("Saved month detail card to %s", path)

    caption = graphics.build_year_caption(year)
    record_path = os.path.join(output_dir, "overview.json")
    preview_and_post(image_path, caption, record_path)


def main():
    setup_logging()
    load_dotenv()

    parser = argparse.ArgumentParser(description="Post PSE dividend graphics to Facebook.")
    parser.add_argument("mode", choices=["month", "year"], help="which graphic to build and post")
    args = parser.parse_args()

    (main_month if args.mode == "month" else main_year)()


if __name__ == "__main__":
    main()
