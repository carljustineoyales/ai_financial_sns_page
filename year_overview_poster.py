"""Posts a full-year (Jan-Dec) dividend payout overview graphic to the
configured Facebook Page, scoped to the PSEi + REIT watchlist.
"""

import calendar
import json
import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv

import rendering as renderer
from assets_logos import ensure_logos
from dividend_tracker import _parse_pse_date, _symbol_lookup, get_watchlist_symbols
from posters.facebook import post_photo
from scraper.pse_edge import get_dividends_and_rights

OUTPUT_DIR = os.path.join("output", "year_overview")


def year_output_dir(year):
    return os.path.join(OUTPUT_DIR, str(year))

DISCLAIMER = (
    "We are not financial advisors. This is for educational purposes only. "
    "Do your own research before investing."
)
HASHTAGS = "#PSE #InvestPH #PersonalFinanceTracker #DividendCalendar"


def get_current_year_by_month(entries, watchlist, symbol_lookup, year=None):
    """{month (1-12): sorted [symbol, ...]} of watchlist tickers with a
    payment_date falling in year (defaults to the current year).
    """
    year = year or date.today().year

    by_month = {m: set() for m in range(1, 13)}
    for entry in entries:
        symbol = symbol_lookup.get(entry["cmpy_id"])
        if not symbol or symbol not in watchlist:
            continue

        parsed = _parse_pse_date(entry["payment_date"])
        if not parsed or parsed.year != year:
            continue

        by_month[parsed.month].add(symbol)

    return {month: sorted(symbols) for month, symbols in by_month.items()}


def build_card(months_data, year, output_path):
    title = f"{year} DIVIDEND PAYOUT CALENDAR"
    subtitle = "PSEi and REIT watchlist"
    footer_lines = [DISCLAIMER]

    ensure_logos(symbol for symbols in months_data.values() for symbol in symbols)

    return renderer.render_year_overview(year, months_data, title, subtitle, footer_lines, output_path)


def build_month_detail_cards(months_data, year, output_dir):
    """Renders a supplementary "zoomed in" full-ticker-list detail image
    for every month that has at least one dividend payer (months with
    none get no detail image -- there's nothing to zoom into). Returns
    the list of paths generated.
    """
    footer_lines = [DISCLAIMER]
    paths = []

    for month, symbols in months_data.items():
        if not symbols:
            continue

        month_name = calendar.month_name[month]
        title = f"{month_name.upper()} {year} DIVIDEND PAYERS"
        subtitle = "PSEi and REIT watchlist"
        output_path = os.path.join(output_dir, f"{month:02d}-{month_name.lower()}.png")

        renderer.render_ticker_logo_grid(title, subtitle, symbols, footer_lines, output_path)
        paths.append(output_path)

    return paths


def build_caption(year):
    intro = f"Here's the {year} dividend payout calendar for PSEi and REIT-listed stocks, month by month."
    return f"{intro}\n\n{DISCLAIMER}\n\n{HASHTAGS}"


def main():
    load_dotenv()

    year = date.today().year
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print("Fetching dividend declarations from PSE Edge...")
    entries = get_dividends_and_rights()

    months_data = get_current_year_by_month(entries, watchlist, symbol_lookup, year=year)
    for month in range(1, 13):
        print(f"  {month:02d}: {len(months_data[month])} tickers")

    output_dir = year_output_dir(year)
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "overview.png")
    build_card(months_data, year, image_path)
    print(f"Saved card to {image_path}")

    detail_paths = build_month_detail_cards(months_data, year, output_dir)
    for path in detail_paths:
        print(f"Saved month detail card to {path}")

    caption = build_caption(year)

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

    record_path = os.path.join(output_dir, "overview.json")
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


if __name__ == "__main__":
    main()
