"""Renders the graphic cards to PNG without posting anywhere.

Reuses the real scraping/watchlist logic from dividend_posters.py, but calls
build_month_card()/build_year_card() directly and stops there --
posters.facebook (post_photo/post_to_page) is never imported.

Usage:
    python scripts/render_preview.py calendar   # next month's dividend calendar card
    python scripts/render_preview.py year       # full year overview + month detail cards
    python scripts/render_preview.py both       # both (default)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from dividend_tracker import _symbol_lookup, get_watchlist_symbols
from scraper.pse_edge import get_dividends_and_rights

PREVIEW_DIR = os.path.join("output", "_preview")


def render_calendar():
    from dividend_posters import build_month_card as build_card, get_month_dividend_events, get_next_month

    year, month = get_next_month()
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print(f"Fetching dividend declarations from PSE Edge for {year}-{month:02d}...")
    entries = get_dividends_and_rights()
    events = get_month_dividend_events(entries, watchlist, symbol_lookup, year, month)
    print(f"{len(events)} watchlist dividend events for {year}-{month:02d}.")

    if not events:
        print("Nothing scheduled in this window -- nothing to render.")
        return

    os.makedirs(PREVIEW_DIR, exist_ok=True)
    output_path = os.path.join(PREVIEW_DIR, f"calendar-{year}-{month:02d}.png")
    build_card(events, year, month, output_path)
    print(f"Saved {output_path}")


def render_year():
    from dividend_posters import build_year_card as build_card, build_month_detail_cards, get_current_year_by_month
    from datetime import date

    year = date.today().year
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print("Fetching dividend declarations from PSE Edge...")
    entries = get_dividends_and_rights()
    months_data = get_current_year_by_month(entries, watchlist, symbol_lookup, year=year)
    for month in range(1, 13):
        print(f"  {month:02d}: {len(months_data[month])} tickers")

    output_dir = os.path.join(PREVIEW_DIR, "year_overview", str(year))
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "overview.png")
    build_card(months_data, year, image_path)
    print(f"Saved {image_path}")

    detail_paths = build_month_detail_cards(months_data, year, output_dir)
    for path in detail_paths:
        print(f"Saved {path}")


def main():
    load_dotenv()
    target = sys.argv[1] if len(sys.argv) > 1 else "both"

    if target in ("calendar", "both"):
        render_calendar()
    if target in ("year", "both"):
        render_year()


if __name__ == "__main__":
    main()
