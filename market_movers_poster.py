"""Posts Top 10 Gainers, Top 10 Losers, and Top 10 Most Active graphics to
the configured Facebook Page, market-wide (not scoped to any watchlist --
same full-market, objective-reporting rule as market_movers.py itself and
financial_report_cards.py). Each category is its own post. Card/caption
generation lives in market_movers_graphics.py; this module handles
data-fetch orchestration, preview/confirm, and posting.

Shares a same-day cached movers snapshot with financial_report_cards.py
via scraper.market_movers.get_or_compute_movers -- whichever of the two
scripts (or scraper/market_movers.py's own cron job) runs first for the
day computes it live and caches it; the rest read that cache, so both
posts reference the exact same top-10 lists without needing a particular
run order.
"""

import logging
import os
import sys
from datetime import date

from dotenv import load_dotenv

import market_movers_graphics as graphics
from logging_config import setup_logging
from posters.preview_and_post import preview_and_post
from scraper.market_movers import get_or_compute_movers, refresh_company_directory

OUTPUT_DIR = os.path.join("output", "market_movers_poster")
TOP_N = 10

logger = logging.getLogger(__name__)


def _fail(stage, exc):
    logger.error("%s failed: %s", stage, exc)


def _process_category(category, entries):
    if not entries:
        logger.info("%s: no data today, skipping.", category)
        return

    item_dir = os.path.join(OUTPUT_DIR, date.today().isoformat(), category)
    os.makedirs(item_dir, exist_ok=True)

    posted_marker = os.path.join(item_dir, "posted.json")
    if os.path.exists(posted_marker):
        logger.info("%s: already posted, skipping.", category)
        return

    image_path = os.path.join(item_dir, "card.png")
    graphics.build_movers_card(category, entries, image_path)
    logger.info("%s: saved card to %s", category, image_path)

    caption = graphics.build_movers_caption(category, entries)
    preview_and_post(image_path, caption, posted_marker)


def main():
    setup_logging()
    load_dotenv()

    logger.info("Refreshing company directory...")
    companies = refresh_company_directory()

    logger.info("Fetching today's market movers (cached snapshot if one already exists)...")
    try:
        movers = get_or_compute_movers(companies, top_n=TOP_N)
    except Exception as e:
        _fail("computing market movers", e)
        sys.exit(1)

    for category, entries in movers.items():
        _process_category(category, entries)


if __name__ == "__main__":
    main()
