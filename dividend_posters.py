"""Posts PSE dividend graphics to the configured Facebook Page: a
next-month dividend ex-date calendar card ("month") and a full-year
(Jan-Dec) dividend payout overview card plus per-month detail cards
("year"). Graphic generation lives in dividend_graphics.py; this module
handles data-fetch orchestration, preview/confirm, and posting.
"""

import argparse
import json
import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv

import dividend_graphics as graphics
from dividend_tracker import _symbol_lookup, get_watchlist_symbols
from posters.facebook import post_photo
from scraper.pse_edge import get_dividends_and_rights


def _preview_and_post(image_path, caption, record_path):
    print("\n" + "-" * 60)
    print("POST PREVIEW")
    print("-" * 60)
    print(f"[image: {image_path}]")
    print(caption)
    print("-" * 60)

    post_mode = os.environ.get("POST_MODE", "confirm")
    if post_mode == "confirm":
        answer = input("\nPost this to Facebook? [y/N]: ").strip().lower()
        if answer != "y":
            print("Not posted.")
            return

    print("Posting to Facebook...")
    post_id = post_photo(image_path, caption)
    print(f"Posted. Post id: {post_id}")

    with open(record_path, "w") as f:
        json.dump(
            {
                "post_id": post_id,
                "caption": caption,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


def main_month():
    year, month = graphics.get_next_month()
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print(f"Fetching dividend declarations from PSE Edge for {year}-{month:02d}...")
    entries = get_dividends_and_rights()

    events = graphics.get_month_dividend_events(entries, watchlist, symbol_lookup, year, month)
    print(f"{len(events)} watchlist dividend events for {year}-{month:02d}.")

    if not events:
        print("Nothing scheduled in this window -- skipping post.")
        return

    os.makedirs(graphics.MONTH_OUTPUT_DIR, exist_ok=True)
    image_name = f"{year}-{month:02d}"
    image_path = os.path.join(graphics.MONTH_OUTPUT_DIR, f"{image_name}.png")
    graphics.build_month_card(events, year, month, image_path)
    print(f"Saved card to {image_path}")

    caption = graphics.build_month_caption()
    record_path = os.path.join(graphics.MONTH_OUTPUT_DIR, f"{image_name}.json")
    _preview_and_post(image_path, caption, record_path)


def main_year():
    year = date.today().year
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print("Fetching dividend declarations from PSE Edge...")
    entries = get_dividends_and_rights()

    months_data = graphics.get_current_year_by_month(entries, watchlist, symbol_lookup, year=year)
    for month in range(1, 13):
        print(f"  {month:02d}: {len(months_data[month])} tickers")

    output_dir = graphics.year_output_dir(year)
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "overview.png")
    graphics.build_year_card(months_data, year, image_path)
    print(f"Saved card to {image_path}")

    detail_paths = graphics.build_month_detail_cards(months_data, year, output_dir)
    for path in detail_paths:
        print(f"Saved month detail card to {path}")

    caption = graphics.build_year_caption(year)
    record_path = os.path.join(output_dir, "overview.json")
    _preview_and_post(image_path, caption, record_path)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Post PSE dividend graphics to Facebook.")
    parser.add_argument("mode", choices=["month", "year"], help="which graphic to build and post")
    args = parser.parse_args()

    (main_month if args.mode == "month" else main_year)()


if __name__ == "__main__":
    main()
